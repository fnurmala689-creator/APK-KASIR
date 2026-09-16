struk_html = f"""
            <html>
                <head>
                    <style>
                        body {{
                            font-family: 'Courier New', monospace;
                            font-size: 11px;
                            width: 200px; /* Ukuran pas untuk kertas thermal 58mm */
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
                        Jl. Raya Sembako No. 45, Jombang
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
                        Barang yang sudah dibeli tidak dapat ditukar.
                    </div>
                </body>
            </html>
            """