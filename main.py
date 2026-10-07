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

def main():
    load_dotenv()  # Loads variables from .env into os.environ
    api_key = os.getenv("OPENAI_API_KEY")
    client = instructor.from_openai(OpenAI(api_key=api_key))
    
    print("AI Order Assistant siap. Ketik pesan pelanggan (atau 'exit' untuk keluar).")
    user_input = input("Anda : ")
    load_stock()
    order = client.create(
        model="gpt-5-nano",
        response_model=Order,  # ini yang memaksa output sesuai struktur Order
        messages=[
            {
            "role": "system", 
            "content": "Kamu adalah asisten yang mengekstrak detail pesanan dari pesan pelanggan toko baju anak online. Ekstrak hanya informasi yang benar-benar disebutkan pelanggan. Jangan mengarang warna, ukuran, atau alamat jika tidak disebutkan secara eksplisit."
        },
            {"role": "user", "content": user_input}
    ])
    stock = {}
    for x in order.order_item:
        stock[(x.product_name, x.color, x.size)] = check_stock(x.product_name.lower(), x.size.lower() if x.size else None, x.color.lower() if x.color else None, x.qty)
    if order.address is None:
        shipping_display = "Alamat belum dimasukkan"
    else:
        rate = calculate_shipping(order.address.lower())
        if rate == 0:
            shipping_display = "Lokasi tidak dikenali"
        else:
            shipping_display = f"Rp{rate}"
        
    print("[Mengekstrak pesanan...]")
    print("[Mengecek stok...]")
    print("[menghitung ongkir...]")
    print("=== Ringkasan pesanan ===")
    i = 1
    for x in order.order_item:
        if(stock[(x.product_name, x.color, x.size)]) : 
            stok = "Tersedia"
        else:
            stok = "Habis"
        print(f"{i}. {x.product_name} - size {x.size} warna {x.color}, {x.qty}pcs - Stok: {stok}")
        i+=1
    print(f"Alamat : {order.address}")
    print(f"Estimasi ongkir : {shipping_display}")

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

def check_stock(product_name, size, color, qty):
    key = (product_name.lower(), size.lower() if size else None, color.lower() if color else None)
    available = stock_data.get(key)
    if available is None:
        return False
    return available >= qty

def calculate_shipping(address):
    # global shipping_rates
    for x in shipping_rates:
        if x in address:
            return shipping_rates[x]
    return 0
    
if __name__ == "__main__":
    main()