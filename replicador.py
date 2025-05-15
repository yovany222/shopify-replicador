import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Credenciais da loja de origem
LOJA1_API_KEY = os.getenv("LOJA1_API_KEY")
LOJA1_API_PASSWORD = os.getenv("LOJA1_API_PASSWORD")
LOJA1_STORE_NAME = os.getenv("LOJA1_STORE_NAME")

# Credenciais da loja de destino
LOJA2_API_KEY = os.getenv("LOJA2_API_KEY")
LOJA2_API_PASSWORD = os.getenv("LOJA2_API_PASSWORD")
LOJA2_STORE_NAME = os.getenv("LOJA2_STORE_NAME")

def buscar_pedidos_loja1():
    url = f"https://{LOJA1_API_KEY}:{LOJA1_API_PASSWORD}@{LOJA1_STORE_NAME}.myshopify.com/admin/api/2023-10/orders.json"
    params = {
        "status": "any",
        "limit": 1,
        "order": "created_at DESC"
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        print("Erro ao buscar pedidos:", response.text)
        return []
    return response.json().get("orders", [])

def criar_pedido_loja2(pedido):
    url = f"https://{LOJA2_API_KEY}:{LOJA2_API_PASSWORD}@{LOJA2_STORE_NAME}.myshopify.com/admin/api/2023-10/orders.json"
    novo_pedido = {
        "order": {
            "line_items": [
                {
                    "title": item["title"],
                    "quantity": item["quantity"],
                    "price": item["price"]
                } for item in pedido.get("line_items", [])
            ],
            "financial_status": "paid"
        }
    }
    response = requests.post(url, json=novo_pedido)
    if response.status_code != 201:
        print("Erro ao criar pedido:", response.text)
    else:
        print("Pedido replicado com sucesso:", response.json().get("order", {}).get("id"))

if __name__ == "__main__":
    pedidos = buscar_pedidos_loja1()
    if pedidos:
        criar_pedido_loja2(pedidos[0])
    else:
        print("Nenhum pedido encontrado na loja de origem.")
