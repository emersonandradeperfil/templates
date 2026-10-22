import csv
import json
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
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
    """Limpa e formata o telefone recolhido."""
    if not telefone:
        return ""
    import re
    return re.sub(r"\s+", " ", telefone).strip()


def criar_driver(headless=False):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--lang=pt-BR")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(45)
    return driver


def detectar_verificacao(driver):
    """Deteta se o Google apresentou CAPTCHA ou bloqueio de tráfego."""
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


def extrair_comentarios(driver, limite=3):
    """Extrai os comentários procurando pelo padrão visual: textos que começam com aspas (")."""
    comentarios = []
    
    # Seletores amplos para capturar blocos de texto na página do Maps
    seletores = [
        "div[role='text']",
        "span.wiI7pd",
        "div.MyEned span",
        "span.MyEned",
        "div.fGCHn span"
    ]
    
    elementos_candidatos = []
    for seletor in seletores:
        try:
            elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
            elementos_candidatos.extend(elementos)
        except Exception:
            pass
            
    # Se não encontrar o suficiente na página principal, tenta clicar na aba de avaliações como fallback
    if len(elementos_candidatos) < limite:
        try:
            botoes = driver.find_elements(By.CSS_SELECTOR, "button[jsaction*='pane.review.tab'], div.F7nice button")
            if botoes:
                botoes[0].click()
                time.sleep(2.5)
                for seletor in seletores:
                    elementos_candidatos.extend(driver.find_elements(By.CSS_SELECTOR, seletor))
        except Exception:
            pass

    # "Lê" igual a você: valida se o texto começa com aspas (", “) indicando um comentário real
    for elemento in elementos_candidatos:
        try:
            texto = elemento.text.strip()
            # Garante que o texto existe, tem tamanho razoável e começa com aspas
            if texto and (texto.startswith('"') or texto.startswith('“')) and len(texto) > 5:
                if texto not in comentarios:
                    comentarios.append(texto)
                    if len(comentarios) >= limite:
                        break
        except Exception:
            pass

    return " | ".join(comentarios[:limite]) if comentarios else "Sem comentários"


def extrair_detalhes_url(driver, url, nome_customizado=""):
    """Acede diretamente ao link do Maps e extrai os dados."""
    driver.get(url)
    time.sleep(3.5)

    if detectar_verificacao(driver):
        return None

    nome = nome_customizado or primeiro_texto(driver, ["h1.DUwDvf", "h1"], "Nome não encontrado")
    
    telefone = normalizar_telefone(
        primeiro_texto(driver, [
            "button[data-item-id^='phone:'] div.fontBodyMedium",
            "button[data-item-id*='phone'] div.fontBodyMedium",
            "a[href^='tel:']"
        ], "")
    )
    
    website = primeiro_atributo(driver, [
        "a[data-item-id='authority']",
        "a[aria-label*='Website']",
        "a[aria-label*='Site']"
    ], "href", "")
    
    endereco = primeiro_texto(driver, [
        "button[data-item-id='address'] div.fontBodyMedium",
        "[data-item-id='address']"
    ], "")
    
    categoria = primeiro_texto(driver, [
        "button[jsaction*='category']",
        "button.DkEaL"
    ], "")
    
    avaliacao = primeiro_texto(driver, [
        "div.F7nice span[aria-hidden='true']",
        "div.F7nice"
    ], "")

    # Recolhe os comentários aplicando o filtro de padrão visual
    comentarios = extrair_comentarios(driver, limite=3)

    return {
        "nome": nome,
        "telefone": telefone,
        "endereco": endereco,
        "categoria": categoria,
        "avaliacao": avaliacao,
        "comentarios": comentarios,
        "website": website,
        "google_maps": driver.current_url,
    }


def salvar_resultados(dados):
    """Guarda os dados recolhidos num ficheiro CSV e JSON."""
    pasta = Path("saida")
    pasta.mkdir(exist_ok=True)

    campos = [
        "id",
        "nome",
        "telefone",
        "endereco",
        "categoria",
        "avaliacao",
        "comentarios",
        "website",
        "google_maps",
    ]

    arquivo_csv = pasta / "prestadoras_avaliacoes.csv"
    arquivo_json = pasta / "prestadoras_avaliacoes.json"

    with arquivo_csv.open("w", newline="", encoding="utf-8-sig") as arquivo:
        writer = csv.DictWriter(arquivo, fieldnames=campos)
        writer.writeheader()
        writer.writerows(dados)

    with arquivo_json.open("w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=4)

    return arquivo_csv, arquivo_json


def processar_lista(empresas, headless=False):
    driver = criar_driver(headless=headless)
    resultados = []

    try:
        print("=" * 65)
        print("EXTRACTOR DE AVALIAÇÕES E COMENTÁRIOS - GOOGLE MAPS")
        print("=" * 65)

        for indice, item in enumerate(empresas, 1):
            print(f"[{indice}/{len(empresas)}] A processar: {item['nome']}...")
            try:
                dados = extrair_detalhes_url(driver, item["url"], item["nome"])
                
                if dados is None:
                    print("[!] Verificação do Google detetada. A interromper.")
                    break

                dados["id"] = indice
                resultados.append(dados)
                
                print(f"    -> Nota: {dados['avaliacao'] or 'N/A'} | Comentários: {dados['comentarios']}")

            except Exception as e:
                print(f"    -> Erro ao processar {item['nome']}: {e}")

            time.sleep(2)

        csv_path, json_path = salvar_resultados(resultados)

        print("\n" + "=" * 65)
        print("EXTRAÇÃO CONCLUÍDA COM SUCESSO")
        print("=" * 65)
        print(f"Ficheiro CSV:  {csv_path}")
        print(f"Ficheiro JSON: {json_path}")
        print("=" * 65)

        return resultados

    finally:
        driver.quit()


if __name__ == "__main__":
    lista_prestadoras = [
        {
            "nome": "Corpus",
            "url": "https://www.google.com/maps/place/Corpus+Saneamento+e+Obras/@-23.2861185,-47.1496853,10z/data=!4m10!1m2!2m1!1scorpus+saneamento+e+obras+ltda!3m6!1s0x94ce63301e7304ab:0x5ada8d621e62dcff!8m2!3d-23.4924241!4d-46.4185787!15sCh5jb3JwdXMgc2FuZWFtZW50byBlIG9icmFzIGx0ZGGSARJ1dGlsaXR5X2NvbnRyYWN0b3LgAQA!16s%2Fg%2F11fn0d2fjj?entry=ttu&g_ep=EgoyMDI2MTAxOS4wIKXMDSoASAFQAw%3D%3D"
        }
    ]

    processar_lista(lista_prestadoras, headless=False)