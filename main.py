from pydantic import BaseModel
import instructor
from dotenv import load_dotenv
import os
from openai import OpenAI
import json

class OrderItem(BaseModel):
    product_name: str
    color: str | None = None
    size: str | None = None
    qty: int

class Order(BaseModel):
    address: str | None = None
    note : str | None = None
    order_item: list[OrderItem]
    
stock_data = {}

shipping_rates = {
    "medan": 15000,
    "jakarta": 25000,
    "surabaya": 25000,
}
tools = [
    {
        "type": "function",
        "name": "check_stock",
        "description": "checking the stock of the product requested by the user",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Name of product requested",
                },
                "size": {
                    "type": ["string", "null"],
                    "description": "size of the product requested, null if the customer does not specify",
                },
                "color": {
                    "type": ["string", "null"],
                    "description": "color of the product requested, null if the customer does not specify",
                }
            },
            "required": ["product_name", "color", "size"],
        },
    },
    {
        "type": "function",
        "name": "calculate_shipping",
        "description": "calculate shipping costs based on the address provided by the customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Address provided by the customer",
                    },
                },
                "required": ["address"],
            },
        },
]
def main():
    load_dotenv()  # Loads variables from .env into os.environ
    api_key = os.getenv("OPENAI_API_KEY")
    # client_1 = instructor.from_openai(OpenAI(api_key=api_key))
    client = OpenAI(
            api_key=api_key,
        )
    print("AI Order Assistant siap. Ketik pesan pelanggan (atau 'exit' untuk keluar).")
  
    input_list = []
    load_stock()
    daftar_produk = sorted({key[0] for key in stock_data})
    system_prompt = f"""
        Kamu adalah asisten toko baju anak online.
        Jawab menggunakan bahasa Indonesia yang ramah.
        Produk yang tersedia: {", ".join(daftar_produk)}.
    
        Jika informasi pesanan belum lengkap, tanyakan
        informasi yang masih diperlukan kepada pelanggan
        informasi yang diberikan pelanggan hanya dalam bentuk teks,
        jangan minta kirim gambar.
    
        Gunakan tool check_stock untuk memeriksa stok
        jika informasi produk dan jumlah sudah tersedia.
        jika warna dan ukuran kosong berikan nilai null
        Gunakan tool calculate_shipping untuk menghitung ongkir
        Ongkir cukup dihitung dari nama kota, jangan meminta 
        alamat lengkap untuk menghitung ongkir
    
        Jangan pernah mengarang informasi stok.
        Sampaikan hasil berdasarkan hasil tool.
        """
    while True:
        user_input = input("Anda : ")
        if(user_input == "exit"):
            break
        input_list.append({"role" : "user", "content" : user_input})
        while True:
            response = client.responses.create(
                                            model="gpt-6-astra",
                                            tools=tools,
                                            instructions=system_prompt,
                                            input=input_list
                                        )
            input_list += response.output
            calls = [i for i in response.output if i.type == "function_call"]
            if not calls:
                print(f"Bot : {response.output_text}")
                break
            for call in calls:
                result = run_tool(call.name, json.loads(call.arguments))
                input_list.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result),
                })

def run_tool(name, args):
    try:
        if(name == "check_stock"):
            return check_stock(**args)
        elif(name == "calculate_shipping"):
            shipping_rate = calculate_shipping(args["address"])
            if(shipping_rate is None):
                return {"error": "Kota tidak dikenal"}
            else:
                return {"shipping_rate": shipping_rate}
        else:
            return {"error": "Tool tidak dikenal"}
    except Exception as e:
        return {"error": f"Tool gagal dijalankan: {e}"}

def load_stock():
    global stock_data
    try :
        with open('stock.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
            stock_data = {
                tuple(key): value
                for key, value in data
            }
    except Exception as e:
        print(f"Error fetching data: {e}")

def check_stock(product_name, size, color):
    matches = [
        (key, qty) for key, qty in stock_data.items()
        if key[0] == product_name.lower()
    ]
    if not matches:
        return {"status": "tidak ditemukan"}

    key = (product_name.lower(), size.lower() if size else None, color.lower() if color else None)
    if key in stock_data:
        qty = stock_data[key]
        return {"status": "habis"} if qty == 0 else {"status": "tersedia", "stok": qty}

    varian = [{"size": k[1], "color": k[2]} for k, _ in matches]
    return {"status": "varian tidak ada", "varian_tersedia": varian}

def calculate_shipping(address):
    # global shipping_rates
    address = address.lower()
    for x in shipping_rates:
        if x in address:
            return shipping_rates[x]
    return None
    
if __name__ == "__main__":
    main()