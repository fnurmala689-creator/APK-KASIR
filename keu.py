pesan_wa = (
                "*NOTA BELANJA - TOKO JABON KIDUL SEPUR*\n"
                "----------------------------------\n"
                f"Tanggal : {waktu_sekarang}\n"
                f"Kepada : {nama_pembeli}\n"
                "----------------------------------\n"
            )
            for item in item_valid:
                pesan_wa += (
                    f"• {item['Nama Barang']}\n"
                    f"  {rp(item['Harga Satuan'])} x {item['Qty']} = *Rp {rp(item['Subtotal'])}*\n\n"
                )
            pesan_wa += "----------------------------------\n"
            if rincian:
                for lbl, val in rincian:
                    pesan_wa += f"{lbl}: Rp {val}\n"
                pesan_wa += "----------------------------------\n"
            pesan_wa += (
                f"Total    : *Rp {total_str}*\n"
                f"Tunai    : Rp {tunai_str}\n"
                f"Kembalian: Rp {kembalian_str}\n"
                "----------------------------------\n"
                "Terima Kasih & Semoga Berkah"
            )
            whatsapp_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(pesan_wa)}"

            col_ble, col_wa = st.columns(2)
            with col_ble:
                data_b64 = base64.b64encode(bytes(raw_bytes)).decode()
                components.html(HTML_CETAK_BLE.replace("__DATA__", data_b64), height=110)
            with col_wa:
                st.markdown(f"""
<div style="text-align: center;">
    <a href="{whatsapp_url}" target="_blank" style="background-color: #25d366; color: white; padding: 14px 20px; text-decoration: none; font-size: 18px; border-radius: 12px; font-weight: bold; display: block; margin-top: 2px;">
        💬 Kirim via WhatsApp
    </a>
</div>
""", unsafe_allow_html=True)
