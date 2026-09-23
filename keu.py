getattr(st, tipe)(teks)

st.markdown("### 🛒 Daftar Belanjaan")
        st.info("💡 Ketik nama barang atau barcode di kolom **Barcode / Kode**, maka daftar pilihan akan muncul secara otomatis. Tekan **Enter** untuk memilih.")
        st.info("💡 Ketik nama barang atau barcode di kolom **Barcode / Kode**, pilih dari dropdown, dan sistem akan langsung memprosesnya.")

# Siapkan string opsi HTML untuk datalist
options_html = ""
@@ -613,14 +613,15 @@ def simpan_barang(kol_barcode, kol_nama, kol_harga_list):
with row_c0:
val_bc = item.get("Barcode", "")

                # Menggabungkan input dan datalist di DALAM satu komponen iframe yang sama
                # Menggabungkan input, datalist, dan event onchange agar langsung otomatis memproses saat diklik/dipilih
components.html(f"""
               <div style="margin: 0px; padding: 0px; font-family: sans-serif;">
                 <input type="text" id="bc_{idx}" value="{val_bc}" placeholder="Ketik/Scan..." 
                        list="list_produk_{idx}" 
                        style="width: 100%; padding: 8px 10px; font-size: 16px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;"
                        onkeydown="if(event.key === 'Enter') {{ parent.document.getElementById('hidden_submit_{idx}').click(); }}"
                         oninput="parent.document.getElementById('val_{idx}').value = this.value;" />
                         oninput="parent.document.getElementById('val_{idx}').value = this.value;"
                         onchange="parent.document.getElementById('val_{idx}').value = this.value; parent.document.getElementById('hidden_submit_{idx}').click();" />
                 <datalist id="list_produk_{idx}">
                   {options_html}
                 </datalist>
