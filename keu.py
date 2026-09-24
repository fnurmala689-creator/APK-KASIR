for idx, item in enumerate(st.session_state.keranjang):
            row_c0, row_c0_cam, row_c1, row_c2, row_c3, row_c4 = st.columns([1.8, 0.5, 3, 2, 2, 1])
            
            # Ambil daftar pilihan produk untuk dropdown
            list_pilihan_produk = [""] + [str(row[kolom_barcode]) + " - " + str(row[kolom_nama_barang]) for _, row in df_produk.iterrows() if kolom_barcode]
            
            with row_c0:
                input_terpilih = st.selectbox(
                    "Barcode / Nama",
                    options=list_pilihan_produk,
                    key=f"input_bc_{idx}_{st.session_state.editor_counter}",
                    label_visibility="collapsed"
                )
                # Jika user memilih dari dropdown, ambil bagian barcodenya saja
                if input_terpilih and " - " in input_terpilih:
                    val_hasil = input_terpilih.split(" - ")[0].strip()
                    if val_hasil != item.get("Barcode", ""):
                        kol_harga_temp = f"Harga {jenis_pelanggan}"
                        if kol_harga_temp not in df_produk.columns:
                            kol_harga_temp = "Harga Umum" if "Harga Umum" in df_produk.columns else df_produk.columns[1]
                        proses_input_barcode(idx, val_hasil, kol_harga_temp)
                        st.rerun()

            with row_c0_cam:
                st.markdown("<div style='margin-top: 2px;'>", unsafe_allow_html=True)
                if st.button("📷", key=f"btn_cam_{idx}", help="Scan Kamera"):
                    st.session_state.scan_counter_kasir_aktif = idx
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            with row_c1:
                st.markdown(f"**{idx + 1}. {item['Nama Barang']}**<br><span style='color:gray; font-size:14px;'>@ Rp {rp(item['Harga Satuan'])}</span>", unsafe_allow_html=True)
            with row_c2:
                sub_q1, sub_q2, sub_q3 = st.columns([1, 1, 1])
                with sub_q1:
                    if st.button("➖", key=f"min_{idx}", use_container_width=True):
                        ubah_qty_langsung(idx, -1)
                        st.rerun()
                with sub_q2:
                    st.markdown(f"<div style='text-align: center; font-weight: bold; padding-top: 5px;'>{item['Qty']}</div>", unsafe_allow_html=True)
                with sub_q3:
                    if st.button("➕", key=f"plus_{idx}", use_container_width=True):
                        ubah_qty_langsung(idx, 1)
                        st.rerun()
            with row_c3:
                item["Subtotal"] = int(item["Qty"]) * int(item["Harga Satuan"])
                st.markdown(f"**Rp {rp(item['Subtotal'])}**")
            with row_c4:
                if st.button("🗑️", key=f"del_{idx}", use_container_width=True):
                    hapus_item_satuan(idx)
                    st.rerun()

            if "_dropdown_pilihan" in item:
                st.markdown(f"🔽 **Pilih barang untuk baris {idx+1}:**")
                for p_idx, (p_bcode, p_nm, p_hg) in enumerate(item["_dropdown_pilihan"]):
                    if st.button(f"👉 [{p_bcode}] {p_nm} - Rp {rp(p_hg)}", key=f"drop_{idx}_{p_idx}", use_container_width=True):
                        pilih_dari_dropdown(idx, p_bcode, p_nm, p_hg)
                        st.rerun()

            st.markdown("---")
