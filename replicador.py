import requests
import time
import urllib3
from datetime import datetime, timedelta
import json
import os

# Desabilita warnings por usar verify=False no requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === CONFIGURAÇÕES DAS LOJAS ===
LOJA1_ACCESS_TOKEN = "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"
LOJA1_STORE_NAME = "qnnsdm-yx"

LOJA2_ACCESS_TOKEN = "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"
LOJA2_STORE_NAME = "2909ea-ea"

# Arquivo para guardar o timestamp do último pedido replicado
ARQUIVO_ULTIMO_PEDIDO = "ultimo_pedido.txt"


def ler_ultimo_pedido_timestamp():
    if os.path.exists(ARQUIVO_ULTIMO_PEDIDO):
        with open(ARQUIVO_ULTIMO_PEDIDO, "r") as f:
            data_str = f.read().strip()
            if data_str:
                return datetime.fromisoformat(data_str)
    # Se não existe arquivo ou está vazio, retorna 1 dia atrás
    return datetime.utcnow() - timedelta(days=1)


def salvar_ultimo_pedido_timestamp(timestamp):
    with open(ARQUIVO_ULTIMO_PEDIDO, "w") as f:
        f.write(timestamp.isoformat())


def buscar_pedidos_novos(desde):
    print(f"[CHECKPOINT] Buscando pedidos da loja 1 criados a partir de {desde.isoformat()}...")

    url = f"https://{LOJA1_STORE_NAME}.myshopify.com/admin/api/2023-10/orders.json"
    headers = {
        "X-Shopify-Access-Token": LOJA1_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    params = {
        "status": "any",
        "limit": 250,  # max permitido por requisição
        "order": "created_at asc",  # ordena do mais antigo pro mais novo
        "created_at_min": desde.isoformat() + "Z"  # filtro a partir dessa data UTC (Z)
    }

    pedidos = []
    page_info = None

    while True:
        if page_info:
            params['page_info'] = page_info

        response = requests.get(url, headers=headers, params=params, verify=False)

        if response.status_code != 200:
            raise Exception(f"Erro ao buscar pedidos: {response.status_code} - {response.text}")

        dados = response.json()
        pedidos_atual = dados.get("orders", [])
        pedidos.extend(pedidos_atual)

        # Shopify usa paginação com "Link" no header, se existir next
        link_header = response.headers.get('Link', '')
        if 'rel="next"' not in link_header:
            break

        # extrai o page_info do link next
        import re
        match = re.search(r'<[^>]+page_info=([^&>]+)[^>]*>; rel="next"', link_header)
        if match:
            page_info = match.group(1)
            # Para próxima página, não usa created_at_min
            params.pop('created_at_min', None)
        else:
            break

    return pedidos


def replicar_pedido_para_loja2(pedido):
    print(f"[CHECKPOINT] Replicando pedido #{pedido['id']} para a loja 2...")

    url = f"https://{LOJA2_STORE_NAME}.myshopify.com/admin/api/2023-10/orders.json"
    headers = {
        "X-Shopify-Access-Token": LOJA2_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    novo_pedido = {
        "order": {
            "line_items": pedido["line_items"],
            "customer": pedido["customer"],
            "billing_address": pedido["billing_address"],
            "shipping_address": pedido["shipping_address"],
            "financial_status": "paid"
        }
    }

    response = requests.post(url, headers=headers, json=novo_pedido, verify=False)

    if response.status_code != 201:
        raise Exception(f"Erro ao criar pedido na loja 2: {response.status_code} - {response.text}")

    print(f"[SUCESSO] Pedido replicado com sucesso para a loja 2!")


if __name__ == "__main__":
    print("=== Iniciando replicação de pedidos entre lojas Shopify ===")

    while True:
        try:
            ultimo_timestamp = ler_ultimo_pedido_timestamp()
            pedidos_novos = buscar_pedidos_novos(ultimo_timestamp)

            if not pedidos_novos:
                print("[INFO] Nenhum pedido novo encontrado.")
            else:
                for pedido in pedidos_novos:
                    replicar_pedido_para_loja2(pedido)

                # Atualiza timestamp para o último pedido replicado
                ultimo_pedido_dt = datetime.fromisoformat(pedidos_novos[-1]['created_at'].replace('Z', '+00:00'))
                salvar_ultimo_pedido_timestamp(ultimo_pedido_dt)

        except Exception as e:
            print(f"[ERRO] {str(e)}")

        print("[INFO] Aguardando 1 hora para próxima verificação...")
        time.sleep(3600)
