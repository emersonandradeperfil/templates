import argparse
import csv
import json
import re
import time
from pathlib import Path
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options


def primeiro_texto(driver, seletores, default=""):
    """Tenta vários seletores e devolve o primeiro texto encontrado."""
    for seletor in seletores:
        try:
            for elemento in driver.find_elements(By.CSS_SELECTOR, seletor):
                texto = elemento.text.strip()
                if texto:
                    return texto
        except Exception:
            pass
    return default


def primeiro_atributo(driver, seletores, atributo, default=""):
    """Tenta vários seletores e devolve o primeiro atributo válido."""
    for seletor in seletores:
        try:
            for elemento in driver.find_elements(By.CSS_SELECTOR, seletor):
                valor = (elemento.get_attribute(atributo) or "").strip()
                if valor:
                    return valor
        except Exception:
            pass
    return default


def normalizar_telefone(telefone):
    """Aceita telefone fixo ou celular; não exige quantidade de dígitos."""
    if not telefone:
        return ""
    return re.sub(r"\s+", " ", telefone).strip()


def montar_url_busca(termo, local):
    consulta = f"{termo} em {local}"
    return f"https://www.google.com/maps/search/{quote_plus(consulta)}"


def criar_driver(headless=False):
    options = Options()

    # Para o primeiro teste, deixe headless=False para enxergar o Chrome.
    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--start-maximized")
    options.add_argument("--lang=pt-BR")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")

    # Selenium 4 usa o Selenium Manager para gerenciar o driver.
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(45)
    return driver


def aceitar_cookies(driver):
    seletores = [
        "button[aria-label*='Accept']",
        "button[aria-label*='Aceitar']",
        "button[aria-label*='Concordo']",
        "button[jsname='b3VHJd']",
    ]

    for seletor in seletores:
        try:
            for botao in driver.find_elements(By.CSS_SELECTOR, seletor):
                if botao.is_displayed():
                    botao.click()
                    time.sleep(1)
                    return
        except Exception:
            pass


def detectar_verificacao(driver):
    """Detecta CAPTCHA/verificação e para sem tentar contorná-la."""
    try:
        texto = driver.find_element(By.TAG_NAME, "body").text.lower()
    except Exception:
        return False

    termos = (
        "unusual traffic",
        "tráfego incomum",
        "captcha",
        "recaptcha",
        "verify you are human",
        "verifique se você é humano",
    )
    return any(termo in texto for termo in termos)


def coletar_links_dos_resultados(driver, limite_links=40, max_rolagens=15):
    """Coleta URLs dos perfis encontrados na lista do Maps."""
    links = []
    vistos = set()
    sem_novidade = 0

    for _ in range(max_rolagens):
        if detectar_verificacao(driver):
            print("\n[!] O Google apresentou uma verificação. Coleta encerrada.")
            break

        elementos = driver.find_elements(
            By.CSS_SELECTOR,
            "div.Nv2PK a.hfpxzc[href], div.Nv2PK a[href*='/maps/place/']",
        )

        antes = len(vistos)

        for elemento in elementos:
            try:
                href = elemento.get_attribute("href")
                if href and "/maps/place/" in href and href not in vistos:
                    vistos.add(href)
                    links.append(href)
                    if len(links) >= limite_links:
                        return links
            except Exception:
                pass

        novos = len(vistos) - antes
        sem_novidade = sem_novidade + 1 if novos == 0 else 0

        if sem_novidade >= 3:
            break

        try:
            feed = driver.find_element(By.CSS_SELECTOR, "div[role='feed']")
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight;", feed
            )
        except Exception:
            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )

        time.sleep(2)

    return links


def extrair_detalhes(driver, url, local):
    """Extrai os dados disponíveis do perfil do estabelecimento."""
    driver.get(url)
    time.sleep(2.5)

    if detectar_verificacao(driver):
        return None

    nome = primeiro_texto(
        driver,
        ["h1.DUwDvf", "h1"],
        "Nome não encontrado",
    )

    # IMPORTANTE:
    # Não existe filtro de celular. Fixo e celular são aceitos.
    telefone = primeiro_texto(
        driver,
        [
            "button[data-item-id^='phone:'] div.fontBodyMedium",
            "button[data-item-id*='phone'] div.fontBodyMedium",
            "button[data-item-id^='phone:']",
            "a[href^='tel:']",
        ],
        "",
    )
    telefone = normalizar_telefone(telefone)

    # O site é usado somente para decidir se o lead será mantido.
    website = primeiro_atributo(
        driver,
        [
            "a[data-item-id='authority']",
            "a[aria-label*='Website']",
            "a[aria-label*='website']",
            "a[aria-label*='Site']",
            "a[href^='http'][data-item-id='authority']",
        ],
        "href",
        "",
    )

    endereco = primeiro_texto(
        driver,
        [
            "button[data-item-id='address'] div.fontBodyMedium",
            "button[data-item-id='address']",
            "[data-item-id='address']",
        ],
        "",
    )

    categoria = primeiro_texto(
        driver,
        [
            "button[jsaction*='category']",
            "button.DkEaL",
        ],
        "",
    )

    avaliacao = primeiro_texto(
        driver,
        [
            "div.F7nice span[aria-hidden='true']",
            "div.F7nice",
        ],
        "",
    )

    return {
        "nome": nome,
        "telefone": telefone,
        "website": website,
        "endereco": endereco,
        "categoria": categoria,
        "avaliacao": avaliacao,
        "local": local,
        "google_maps": driver.current_url,
    }


def salvar_resultados(dados, local):
    pasta = Path("saida")
    pasta.mkdir(exist_ok=True)

    nome_base = re.sub(r"[^a-zA-Z0-9_-]+", "_", local.lower()).strip("_")
    nome_base = nome_base or "resultado"

    campos = [
        "id",
        "nome",
        "telefone",
        "endereco",
        "categoria",
        "avaliacao",
        "website",
        "local",
        "google_maps",
    ]

    arquivo_csv = pasta / f"clinicas_sem_site_{nome_base}.csv"
    arquivo_json = pasta / f"clinicas_sem_site_{nome_base}.json"

    with arquivo_csv.open("w", newline="", encoding="utf-8-sig") as arquivo:
        writer = csv.DictWriter(arquivo, fieldnames=campos)
        writer.writeheader()
        writer.writerows(dados)

    with arquivo_json.open("w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=4)

    return arquivo_csv, arquivo_json


def buscar_clinicas(
    local,
    quantidade=10,
    termo="clínicas",
    limite_busca=None,
    headless=False,
):
    if quantidade <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")

    # Como parte dos resultados terá site e será descartada,
    # coletamos mais candidatos do que a meta final.
    if limite_busca is None:
        limite_busca = max(quantidade * 4, 30)

    print("=" * 65)
    print("GOOGLE MAPS - CLÍNICAS SEM SITE")
    print("=" * 65)
    print(f"Local:          {local}")
    print(f"Termo:          {termo}")
    print(f"Meta final:     {quantidade}")
    print(f"Candidatos:     até {limite_busca}")
    print("Telefone:       fixo OU celular; não é obrigatório")
    print("=" * 65)

    driver = criar_driver(headless=headless)
    resultados = []
    processados = set()

    try:
        print("\n[1/3] Abrindo Google Maps...")
        driver.get(montar_url_busca(termo, local))
        time.sleep(4)
        aceitar_cookies(driver)

        if detectar_verificacao(driver):
            print("[!] Google apresentou uma verificação. Tente novamente mais tarde.")
            return []

        print("[2/3] Coletando perfis...")
        links = coletar_links_dos_resultados(
            driver,
            limite_links=limite_busca,
            max_rolagens=15,
        )
        print(f"      {len(links)} perfis encontrados.")

        print("\n[3/3] Verificando sites e telefones...\n")

        for indice, link in enumerate(links, 1):
            if len(resultados) >= quantidade:
                break

            if link in processados:
                continue
            processados.add(link)

            try:
                dados = extrair_detalhes(driver, link, local)

                if dados is None:
                    print("[!] Verificação detectada. Encerrando.")
                    break

                if dados["website"]:
                    print(
                        f"[{indice}/{len(links)}] IGNORADA (tem site): "
                        f"{dados['nome']}"
                    )
                    continue

                dados["id"] = len(resultados) + 1
                resultados.append(dados)

                telefone = dados["telefone"] or "sem telefone"

                print(
                    f"[OK {len(resultados)}/{quantidade}] "
                    f"{dados['nome']} | {telefone}"
                )

            except TimeoutException:
                print(f"[{indice}/{len(links)}] Timeout - pulando.")
            except WebDriverException as erro:
                print(f"[{indice}/{len(links)}] Erro do navegador - pulando: {erro}")
            except Exception as erro:
                print(f"[{indice}/{len(links)}] Erro - pulando: {erro}")

            time.sleep(1.5)

        csv_path, json_path = salvar_resultados(resultados, local)

        print("\n" + "=" * 65)
        print("FINALIZADO")
        print("=" * 65)
        print(f"Resultados válidos: {len(resultados)}")
        print(f"CSV:  {csv_path}")
        print(f"JSON: {json_path}")
        print("=" * 65)

        return resultados

    finally:
        driver.quit()


def main():
    parser = argparse.ArgumentParser(
        description="Busca clínicas no Google Maps e filtra as que não possuem site."
    )

    parser.add_argument(
        "--local",
        "--bairro",
        dest="local",
        default="Penha de França, São Paulo - SP",
        help="Bairro, região ou cidade da busca.",
    )

    parser.add_argument(
        "--quantidade",
        type=int,
        default=10,
        help="Quantidade final de clínicas sem site.",
    )

    parser.add_argument(
        "--termo",
        default="Podóloga",
        help="Termo pesquisado no Google Maps.",
    )

    parser.add_argument(
        "--limite-busca",
        type=int,
        default=None,
        help="Quantidade máxima de perfis candidatos.",
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Executa o Chrome sem mostrar a janela.",
    )

    args = parser.parse_args()

    buscar_clinicas(
        local=args.local,
        quantidade=args.quantidade,
        termo=args.termo,
        limite_busca=args.limite_busca,
        headless=args.headless,
    )


if __name__ == "__main__":
    main()
