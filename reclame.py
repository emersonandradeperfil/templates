import csv
import json
import os
import re
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def criar_driver(headless=False):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    
    options.add_argument("--start-maximized")
    options.add_argument("--lang=pt-BR")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    
    # USA O SEU PERFIL REAL DO CHROME (substitui o modo anônimo)
    # Pega automaticamente a pasta User Data do Windows do usuário atual
    caminho_perfil = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data")
    options.add_argument(f"user-data-dir={caminho_perfil}")
    options.add_argument("profile-directory=Default")  # Altere para "Profile 1", etc., se usar múltiplos perfis no Chrome
    
    # Oculta o rastro de automação do Selenium
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(45)
    return driver


def fechar_banner_privacidade(driver):
    """Procura e clica no botão 'Aceitar' do aviso de privacidade/cookies."""
    seletores_aceitar = [
        "//button[contains(text(), 'Aceitar')]",
        "//button[contains(@class, 'cookie') or contains(@class, 'privacy')]",
    ]
    
    for xpath in seletores_aceitar:
        try:
            botoes = driver.find_elements(By.XPATH, xpath)
            for botao in botoes:
                if botao.is_displayed():
                    botao.click()
                    time.sleep(1)
                    return True
        except Exception:
            pass
    return False


def extrair_reclame_aqui(driver, url, nome_empresa=""):
    """Navega no Reclame Aqui usando o perfil real, aceita cookies, clica em 'Geral' e extrai os dados."""
    driver.get(url)
    time.sleep(4)

    # 1. Trata o pop-up de cookies/privacidade
    fechar_banner_privacidade(driver)

    # 2. Clica na aba "Geral" dentro de Desempenho
    try:
        aba_geral = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[text()='Geral'] | //a[text()='Geral'] | //li[text()='Geral'] | //*[contains(text(), 'Geral')]")
            )
        )
        driver.execute_script("arguments[0].click();", aba_geral)
        time.sleep(2)
    except Exception as e:
        print(f"    [!] Aviso ao clicar na aba 'Geral': {e}")

    reputacao = "Não encontrada"
    nota_media = "Não encontrada"

    # 3. Extrai a Reputação (ex: RUIM, BOM, ÓTIMO)
    try:
        elementos = driver.find_elements(By.XPATH, "//*[contains(text(), 'RUIM') or contains(text(), 'BOM') or contains(text(), 'ÓTIMO') or contains(text(), 'REGULAR') or contains(text(), 'NÃO RECOMENDADA')]")
        for el in elementos:
            txt = el.text.strip()
            if txt in ["RUIM", "BOM", "ÓTIMO", "REGULAR", "NÃO RECOMENDADA"]:
                reputacao = txt
                break
    except Exception:
        pass

    # 4. Extrai a Nota Média Geral (ex: 5.5) usando Regex
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        
        match = re.search(r"nota\s+média\s+geral\s+([\d[\.,]+)", body_text, re.IGNORECASE)
        if not match:
            match = re.search(r"([\d[\.,]+)\s*/\s*10", body_text)

        if match:
            nota_media = match.group(1).replace(",", ".")
    except Exception:
        pass

    return {
        "empresa": nome_empresa,
        "reputacao_geral": reputacao,
        "nota_media_geral": nota_media,
        "url": url,
    }


def salvar_resultados(dados):
    pasta = Path("saida")
    pasta.mkdir(exist_ok=True)

    campos = ["empresa", "reputacao_geral", "nota_media_geral", "url"]
    arquivo_csv = pasta / "reclame_aqui_resultados.csv"
    arquivo_json = pasta / "reclame_aqui_resultados.json"

    with arquivo_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(dados)

    with arquivo_json.open("w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

    return arquivo_csv, arquivo_json


if __name__ == "__main__":
    empresas = [
        {
            "nome": "Corpus Saneamento e Obras",
            "url": "https://www.reclameaqui.com.br/empresa/corpus-saneamento-e-obras-ltda/"
        }
    ]

    driver = criar_driver(headless=False)
    resultados = []

    try:
        print("=" * 60)
        print("EXTRAINDO DADOS DO RECLAME AQUI (PERFIL REAL DO CHROME)")
        print("=" * 60)

        for item in empresas:
            print(f"A processar: {item['nome']}...")
            dados = extrair_reclame_aqui(driver, item["url"], item["nome"])
            resultados.append(dados)

            print(f" -> Reputação Geral: {dados['reputacao_geral']}")
            print(f" -> Nota Média Geral: {dados['nota_media_geral']}")
            print("-" * 60)

        csv_p, json_p = salvar_resultados(resultados)
        print(f"Sucesso! Arquivos gerados:\n - {csv_p}\n - {json_p}")

    finally:
        driver.quit()