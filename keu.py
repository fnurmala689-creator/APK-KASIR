import streamlit as st
import pandas as pd
from datetime import datetime
import io

st.set_page_config(page_title="Aplikasi Kasir Toko Sembako", page_icon="🏪")

st.title("🏪 Kasir Toko Sembako")
st.markdown("Aplikasi Kasir Praktis & Cetak Struk Thermal 58mm")

# Inisialisasi Database Produk di session_state
if "df_produk" not in st.session_state:
    st.session_state.df_produk = pd.DataFrame({
        "Nama Barang": [
            "Beras Premium 1 Kg", 
            "Minyak Goreng 1 Liter", 
            "Gula Pasir 1 Kg", 
            "Telur Ayam 1 Kg", 
            "Kopi Bubuk 250g",
            "Tepung Terigu 1 Kg"
        ],
        "Harga Modal (HPP)": [13000, 15000, 14000, 24000, 12000, 10000],
        "Harga Jual": [15000, 17500, 16000, 27000, 15000, 12000]
    })

# Inisialisasi keranjang belanja
if "keranjang" not in st.session_state:
    st.session_state.keranjang = []

tab1, tab2 = st.tabs(["🛒 Kasir & Keranjang", "📋 Kelola Daftar Harga"])

with tab2:
    st.subheader("Edit Daftar Barang dan Harga Jual")
    st.session_state.df_produk = st.data_editor(
        st.session_state.df_produk,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_produk"
    )

with tab1:
    st.subheader("1. Cari & Tambah Barang")
    
    keyword_cari = st.text_input("🔍 Cari nama barang:", placeholder="Contoh: minyak, beras, gula...")
    
    df_produk_aktif = st.session_state.df_produk.copy()
    
    if keyword_cari:
        df_produk_aktif = df_produk_aktif[
            df_produk_aktif["Nama Barang"].str.contains(keyword_cari, case=False, na=False)
        ]
    
    if len(df_produk_aktif) > 0:
        col_input1, col_input2, col_input3 = st.columns([2, 1, 1])
        
        with col_input1:
            pilihan_barang = st.selectbox("Pilih Barang:", df_produk_aktif["Nama Barang"])
            data_terpilih = df_produk_aktif[df_produk_aktif["Nama Barang"] == pilihan_barang].iloc[0]
            harga_otomatis = int(data_terpilih["Harga Jual"])
        
        with col_input2:
            qty_pilih = st.number_input("Jumlah (Qty)", min_value=1, value=1)
            
        with col_input3:
            st.write("") 
            st.write("")
            tambah_btn = st.button("➕ Tambah")

        if tambah_btn:
            subtotal = qty_pilih * harga_otomatis
            st.session_state.keranjang.append({
                "Nama Barang": pilihan_barang,
                "Qty": qty_pilih,
                "Harga Satuan": harga_otomatis,
                "Subtotal": subtotal
            })
            st.toast(f"Berhasil menambahkan {pilihan_barang}!", icon="✅")
    else:
        st.warning("Barang tidak ditemukan.")

    st.divider()
    st.subheader("2. Keranjang Belanja")

    if len(st.session_state.keranjang) > 0:
        df_keranjang = pd.DataFrame(st.session_state.keranjang)
        st.dataframe(df_keranjang, use_container_width=True)

        total_belanja_semua = df_keranjang["Subtotal"].sum()
        st.metric(label="TOTAL YANG HARUS DIBAYAR", value=f"Rp {total_belanja_semua:,.0f}")

        col_aksi1, col_aksi2 = st.columns(2)
        with col_aksi1:
            nama_pembeli = st.text_input("Nama Pelanggan", value="Pelanggan Umum")
        with col_aksi2:
            st.write("")
            st.write("")
            if st.button("🗑️ Kosongkan Keranjang"):
                st.session_state.keranjang = []
                st.rerun()

        if st.button("✨ Proses Nota Pembelian"):
            waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Format HTML struk khusus ukuran thermal 58mm (~200px)
            html_items = ""
            for item in st.session_state.keranjang:
                html_items += f"""
                <tr>
                    <td colspan="2"><b>{item['Nama Barang']}</b></td>
                </tr>
                <tr>
                    <td>{item['Qty']} x {item['Harga Satuan']:,.0f}</td>
                    <td style="text-align: right;">{item['Subtotal']:,.0f}</td>
                </tr>
                """

            struk_html = f"""
            <html>
                <head>
                    <style>
                        body {{
                            font-family: 'Courier New', monospace;
                            font-size: 11px;
                            width: 200px;
                            margin: 0 auto;
                            padding: 5px;
                        }}
                        .center {{ text-align: center; }}
                        .line {{ border-bottom: 1px dashed black; margin: 5px 0; }}
                        table {{ width: 100%; border-collapse: collapse; }}
                    </style>
                </head>
                <body>
                    <div class="center">
                        <b>TOKO SEMBAKO BERKAH</b><br>
                        Jombang
                    </div>
                    <div class="line"></div>
                    <div>
                        Tgl : {waktu_sekarang}<br>
                        Pelanggan : {nama_pembeli}
                    </div>
                    <div class="line"></div>
                    <table>
                        {html_items}
                    </table>
                    <div class="line"></div>
                    <table>
                        <tr>
                            <td><b>TOTAL:</b></td>
                            <td style="text-align: right;"><b>Rp {total_belanja_semua:,.0f}</b></td>
                        </tr>
                    </table>
                    <div class="line"></div>
                    <div class="center">
                        TERIMA KASIH!<br>
                        Barang laku tidak ditukar.
                    </div>
                </body>
            </html>
            """

            st.success("Nota berhasil dibuat!")

            # Tombol Cetak Instan Langsung ke Printer Thermal
            st.markdown("### 🖨️ Cetak Struk")
            st.components.v1.html(f"""
                <div style="text-align: center;">
                    <button onclick="printReceipt()" style="background-color: #ff4b4b; color: white; border: none; padding: 10px 18px; font-size: 14px; border-radius: 6px; cursor: pointer; font-weight: bold;">
                        🖨️ Cetak Struk Sekarang
                    </button>
                </div>
                <div id="print-area" style="display:none;">
                    {struk_html}
                </div>
                <script>
                    function printReceipt() {{
                        var content = document.getElementById('print-area').innerHTML;
                        var mywindow = window.open('', 'PRINT', 'height=500,width=280');
                        mywindow.document.write('<html><head><title>Struk</title></head><body>');
                        mywindow.document.write(content);
                        mywindow.document.write('</body></html>');
                        mywindow.document.close();
                        mywindow.focus();
                        mywindow.print();
                        mywindow.close();
                        return true;
                    }}
                </script>
            """, height=70)
            
    else:
        st.info("Keranjang masih kosong. Silakan cari dan tambah barang di atas.")