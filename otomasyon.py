import streamlit as st
import pandas as pd
import datetime
import sqlite3

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Hukuk Otomasyonu", page_icon="⚖️", layout="wide")

# --- 2. VERİTABANI KURULUMU VE BAĞLANTISI ---
def veritabani_kur():
    conn = sqlite3.connect('hukuk.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS davalar (id INTEGER PRIMARY KEY AUTOINCREMENT, esas_no TEXT, mahkeme TEXT, tur TEXT, tarih TEXT, taraf TEXT, durum TEXT, avukat TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS personeller (id INTEGER PRIMARY KEY AUTOINCREMENT, ad_soyad TEXT, gorev TEXT, telefon TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS notlar (id INTEGER PRIMARY KEY AUTOINCREMENT, icerik TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS durusmalar (id INTEGER PRIMARY KEY AUTOINCREMENT, esas_no TEXT, tarih TEXT, saat TEXT, aciklama TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS evraklar (id INTEGER PRIMARY KEY AUTOINCREMENT, esas_no TEXT, evrak_adi TEXT, yuklenme_tarihi TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vekaletler (id INTEGER PRIMARY KEY AUTOINCREMENT, v_no TEXT, muvekkil TEXT, n_adi TEXT, y_no TEXT, n_tarih TEXT, durum TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS raporlar (id INTEGER PRIMARY KEY AUTOINCREMENT, isim TEXT, tarih TEXT, durum TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS finans (id INTEGER PRIMARY KEY AUTOINCREMENT, islem_turu TEXT, miktar REAL, aciklama TEXT, tarih TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS gorevler (id INTEGER PRIMARY KEY AUTOINCREMENT, gorev_adi TEXT, sorumlu TEXT, son_tarih TEXT, durum TEXT)''')
    
    c.execute("SELECT COUNT(*) FROM personeller")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO personeller (ad_soyad, gorev, telefon) VALUES ('Av. Eren', 'Kurucu Avukat', '0532 111 2233')")
        c.execute("INSERT INTO personeller (ad_soyad, gorev, telefon) VALUES ('Av. Ahmet', 'Kıdemli Avukat', '0533 222 3344')")
        c.execute("INSERT INTO notlar (icerik) VALUES ('📅 **Toplantı:** Cuma 14:00''da XYZ Şirketi ile toplantı var.')")
        c.execute("INSERT INTO finans (islem_turu, miktar, aciklama, tarih) VALUES ('Gelir', 15000.0, 'XYZ Ltd. Şti. Vekalet Ücreti', '01.07.2026')")
        c.execute("INSERT INTO gorevler (gorev_adi, sorumlu, son_tarih, durum) VALUES ('Cevap Dilekçesi Yazılacak', 'Av. Ahmet', '10.07.2026', 'Bekliyor')")
        conn.commit()
    conn.close()

veritabani_kur()

# --- 3. HAFIZA (SESSION STATE) ---
if 'aktif_dava_karti' not in st.session_state: st.session_state.aktif_dava_karti = None
if 'dava_duzenle_modu' not in st.session_state: st.session_state.dava_duzenle_modu = False # YENİ: Düzenleme modu hafızası
for sihirbaz in ['dava_sihirbaz', 'vek_sihirbaz', 'rap_sihirbaz']: st.session_state[sihirbaz] = st.session_state.get(sihirbaz, False)
for adim in ['dava_adim', 'vek_adim', 'rap_adim']: st.session_state[adim] = st.session_state.get(adim, 1)
for gecici in ['gecici_dava', 'gecici_vekalet', 'gecici_rapor']: st.session_state[gecici] = st.session_state.get(gecici, {})
if 'hesap_modu' not in st.session_state: st.session_state.hesap_modu = "dava_gideri"

st.title("⚖️ Hukuk Bürosu Otomasyon Sistemi")

tab_ana, tab_dava, tab_vekalet, tab_buro, tab_finans, tab_rapor, tab_hesap = st.tabs([
    "🏠 Ana Sayfa", "📁 Davalar", "📜 Vekaletler", "🏢 Büro & Görevler", "💰 Finans", "📊 Raporlar", "🧮 Hesaplamalar"
])

# ==========================================
# 1. ANA SAYFA
# ==========================================
with tab_ana:
    st.subheader("📊 Ofis Gösterge Paneli")
    conn = sqlite3.connect('hukuk.db')
    dava_sayisi = pd.read_sql_query("SELECT COUNT(*) FROM davalar", conn).iloc[0,0]
    gorev_sayisi = pd.read_sql_query("SELECT COUNT(*) FROM gorevler WHERE durum='Bekliyor'", conn).iloc[0,0]
    df_finans = pd.read_sql_query("SELECT islem_turu, miktar FROM finans", conn)
    toplam_gelir = df_finans[df_finans['islem_turu'] == 'Gelir']['miktar'].sum()
    toplam_gider = df_finans[df_finans['islem_turu'] == 'Gider']['miktar'].sum()
    kasa_bakiye = toplam_gelir - toplam_gider
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Açık Dosya Sayısı", f"{dava_sayisi} Dosya")
    c2.metric("Bekleyen Görevler", f"{gorev_sayisi} Görev")
    c3.metric("Aylık Gelir", f"{toplam_gelir:,.2f} ₺")
    c4.metric("Güncel Kasa", f"{kasa_bakiye:,.2f} ₺", delta=f"Gider: -{toplam_gider:,.2f} ₺", delta_color="inverse")
    st.markdown("---")
    
    c_grafik, c_ajanda = st.columns([5, 5])
    with c_grafik:
        st.markdown("#### 📈 Dava Türlerine Göre Dağılım")
        df_grafik = pd.read_sql_query("SELECT tur, COUNT(*) as Sayi FROM davalar GROUP BY tur", conn)
        if not df_grafik.empty: st.bar_chart(df_grafik.set_index("tur"))
        else: st.info("Grafik için yeterli veri yok.")
            
    with c_ajanda:
        st.markdown("#### 📅 Yaklaşan Duruşmalar")
        df_ajanda = pd.read_sql_query("SELECT tarih as Tarih, saat as Saat, esas_no as 'Dosya', aciklama as 'Açıklama' FROM durusmalar ORDER BY tarih ASC LIMIT 5", conn)
        if df_ajanda.empty: st.success("Yakın zamanda planlanmış duruşma yok.")
        else: st.dataframe(df_ajanda, use_container_width=True, hide_index=True)
    conn.close()

# ==========================================
# 2. DAVALAR SEKMESİ (DÜZENLEME MODU EKLENDİ)
# ==========================================
with tab_dava:
    conn = sqlite3.connect('hukuk.db')
    df_dava = pd.read_sql_query("SELECT id as 'B. Dos. No', esas_no as 'Dosya Esas No', mahkeme as 'Mahkeme', tur as 'Dava Tür Adı', tarih as 'Dosya Açılış Tarihi', taraf as 'Tarafımız', durum as 'Durum', avukat as 'Sorumlu Avukat' FROM davalar", conn)
    conn.close()
    
    # 🌟 DAVA KARTI İÇİ
    if st.session_state.aktif_dava_karti is not None:
        secilen = st.session_state.aktif_dava_karti
        dava_bilgisi = df_dava[df_dava["Dosya Esas No"] == secilen].iloc[0]
        
        # Üst Başlık ve Butonlar
        col_geri, col_baslik, col_duzenle = st.columns([2, 6, 2])
        with col_geri:
            if st.button("⬅️ Geri Dön", key="dava_kart_geri"):
                st.session_state.aktif_dava_karti = None
                st.session_state.dava_duzenle_modu = False
                st.rerun()
        with col_baslik:
            st.subheader(f"📂 Dava Kartı Detayı: {secilen}")
        with col_duzenle:
            if not st.session_state.dava_duzenle_modu:
                if st.button("✏️ Düzenle", use_container_width=True, key="btn_duzenle_mod"):
                    st.session_state.dava_duzenle_modu = True
                    st.rerun()
        st.markdown("---")
        
        # 🌟 DÜZENLEME MODU AÇIKSA
        if st.session_state.dava_duzenle_modu:
            st.markdown("### ✏️ Dava Bilgilerini Güncelle")
            c_duz1, c_duz2 = st.columns(2)
            
            with c_duz1:
                yeni_mah = st.text_input("Mahkeme:", value=dava_bilgisi['Mahkeme'], key="e_mah")
                
                # Mevcut değer listede yoksa ekle (Hata vermemesi için)
                tur_listesi = ["Alacak Davası", "Boşanma Davası", "İş Davası", "Ceza Davası"]
                if dava_bilgisi['Dava Tür Adı'] not in tur_listesi: tur_listesi.append(dava_bilgisi['Dava Tür Adı'])
                yeni_tur = st.selectbox("Tür:", tur_listesi, index=tur_listesi.index(dava_bilgisi['Dava Tür Adı']), key="e_tur")
                
                taraf_listesi = ["DAVACI", "DAVALI", "SANIK", "MÜŞTEKİ"]
                if dava_bilgisi['Tarafımız'] not in taraf_listesi: taraf_listesi.append(dava_bilgisi['Tarafımız'])
                yeni_taraf = st.selectbox("Tarafımız:", taraf_listesi, index=taraf_listesi.index(dava_bilgisi['Tarafımız']), key="e_taraf")
            
            with c_duz2:
                try: m_tarih = datetime.datetime.strptime(dava_bilgisi['Dosya Açılış Tarihi'], "%d.%m.%Y").date()
                except: m_tarih = datetime.date.today()
                yeni_tar = st.date_input("Açılış Tarihi:", value=m_tarih, key="e_tar")
                
                durum_listesi = ["Derdest", "Karara Çıktı", "İstinafta"]
                if dava_bilgisi['Durum'] not in durum_listesi: durum_listesi.append(dava_bilgisi['Durum'])
                yeni_durum = st.selectbox("Durum:", durum_listesi, index=durum_listesi.index(dava_bilgisi['Durum']), key="e_durum")
                
                # Veritabanından Avukatları Çek
                conn = sqlite3.connect('hukuk.db')
                df_pers = pd.read_sql_query("SELECT ad_soyad FROM personeller", conn)
                conn.close()
                avu_listesi = df_pers["ad_soyad"].tolist() if not df_pers.empty else ["Avukat Yok"]
                if dava_bilgisi['Sorumlu Avukat'] not in avu_listesi: avu_listesi.append(dava_bilgisi['Sorumlu Avukat'])
                yeni_avu = st.selectbox("Sorumlu Avukat:", avu_listesi, index=avu_listesi.index(dava_bilgisi['Sorumlu Avukat']), key="e_avu")

            # Kaydet / İptal Butonları
            cd_g, cd_i = st.columns([1, 8])
            with cd_g:
                if st.button("❌ İptal", key="e_iptal"):
                    st.session_state.dava_duzenle_modu = False
                    st.rerun()
            with cd_i:
                if st.button("💾 Değişiklikleri Kaydet", type="primary", key="e_kaydet"):
                    conn = sqlite3.connect('hukuk.db')
                    c = conn.cursor()
                    c.execute('''UPDATE davalar SET mahkeme=?, tur=?, tarih=?, taraf=?, durum=?, avukat=? WHERE esas_no=?''', 
                              (yeni_mah, yeni_tur, yeni_tar.strftime("%d.%m.%Y"), yeni_taraf, yeni_durum, yeni_avu, secilen))
                    conn.commit()
                    conn.close()
                    st.session_state.dava_duzenle_modu = False
                    st.rerun()
                    
        # 🌟 DÜZENLEME MODU KAPALIYSA (NORMAL GÖRÜNÜM)
        else:
            c1, c2, c3 = st.columns(3)
            c1.info(f"**Mahkeme:** {dava_bilgisi['Mahkeme']}\n\n**Tür:** {dava_bilgisi['Dava Tür Adı']}")
            c2.warning(f"**Tarafımız:** {dava_bilgisi['Tarafımız']}\n\n**Açılış Tarihi:** {dava_bilgisi['Dosya Açılış Tarihi']}")
            c3.success(f"**Durum:** {dava_bilgisi['Durum']}\n\n**Avukat:** {dava_bilgisi['Sorumlu Avukat']}")
            
            st.markdown("### 📝 Dosya İşlemleri")
            tab_durusma, tab_evrak = st.tabs(["📅 Duruşmalar", "📄 Evraklar"])
            with tab_durusma:
                conn = sqlite3.connect('hukuk.db')
                df_dosya_durusmalari = pd.read_sql_query(f"SELECT id, tarih as 'Tarih', saat as 'Saat', aciklama as 'Açıklama' FROM durusmalar WHERE esas_no='{secilen}' ORDER BY tarih ASC", conn)
                conn.close()
                if df_dosya_durusmalari.empty: st.info("Bu dosyaya ait duruşma bulunmamaktadır.")
                else: st.dataframe(df_dosya_durusmalari.drop(columns=['id']), use_container_width=True, hide_index=True)
                with st.expander("➕ Yeni Duruşma Ekle"):
                    col_d1, col_d2, col_d3 = st.columns(3)
                    d_tarih = col_d1.date_input("Duruşma Tarihi:", key="d_tar")
                    d_saat = col_d2.time_input("Duruşma Saati:", key="d_saat")
                    d_aciklama = col_d3.text_input("Açıklama (Örn: 2. Celse):", key="d_aciklama")
                    if st.button("Duruşmayı Kaydet", type="primary", key="btn_dur_kaydet"):
                        conn = sqlite3.connect('hukuk.db'); c = conn.cursor()
                        c.execute("INSERT INTO durusmalar (esas_no, tarih, saat, aciklama) VALUES (?, ?, ?, ?)", (secilen, d_tarih.strftime("%d.%m.%Y"), d_saat.strftime("%H:%M"), d_aciklama))
                        conn.commit(); conn.close(); st.rerun()
            with tab_evrak:
                conn = sqlite3.connect('hukuk.db')
                df_dosya_evraklari = pd.read_sql_query(f"SELECT evrak_adi as 'Evrak Adı', yuklenme_tarihi as 'Yüklenme Tarihi' FROM evraklar WHERE esas_no='{secilen}'", conn)
                conn.close()
                col_e1, col_e2 = st.columns([6, 4])
                with col_e1:
                    if df_dosya_evraklari.empty: st.info("Bu dosyaya henüz evrak yüklenmemiş.")
                    else: st.dataframe(df_dosya_evraklari, use_container_width=True, hide_index=True)
                with col_e2:
                    yuklenen_dosya = st.file_uploader("Dosyaya Evrak Yükle", accept_multiple_files=False, key="d_evrak")
                    if st.button("Evrak Kaydet", type="primary", key="btn_evrak_kaydet"):
                        if yuklenen_dosya is not None:
                            conn = sqlite3.connect('hukuk.db'); c = conn.cursor()
                            c.execute("INSERT INTO evraklar (esas_no, evrak_adi, yuklenme_tarihi) VALUES (?, ?, ?)", (secilen, yuklenen_dosya.name, datetime.date.today().strftime("%d.%m.%Y")))
                            conn.commit(); conn.close(); st.success("Evrak eklendi!"); st.rerun()

    # 🌟 ANA LİSTE
    else:
        if not st.session_state.dava_sihirbaz:
            col1, col2 = st.columns([8, 2])
            with col1: st.subheader("Dava Yönetimi")
            with col2:
                if st.button("➕ Yeni Dava Kartı Aç", type="primary", use_container_width=True, key="btn_dava_ac"):
                    st.session_state.dava_sihirbaz = True; st.session_state.dava_adim = 1; st.rerun() 
            arama = st.text_input("🔍 Bul (Dosya No veya Dava Türü):", key="dava_arama")
            if arama: df_dava = df_dava[df_dava["Dosya Esas No"].str.contains(arama, case=False) | df_dava["Dava Tür Adı"].str.contains(arama, case=False)]
            st.dataframe(df_dava, use_container_width=True, hide_index=True)
            st.markdown("---")
            if not df_dava.empty:
                secilen_dava = st.selectbox("👇 İşlem Yapmak İstediğiniz Dosyayı Seçin:", ["Seçiniz..."] + df_dava["Dosya Esas No"].tolist(), key="dava_secim")
                if secilen_dava != "Seçiniz...":
                    dava_detay = df_dava[df_dava["Dosya Esas No"] == secilen_dava].iloc[0]
                    with st.expander(f"📌 {secilen_dava} Esas Numaralı Dosyanın Detayları", expanded=True):
                        col_taraf, col_karsi, col_islem = st.columns(3)
                        col_taraf.write(f"**Konum:** {dava_detay['Tarafımız']}\n\n**Avukat:** {dava_detay['Sorumlu Avukat']}") 
                        col_karsi.write(f"**Mahkeme:** {dava_detay['Mahkeme']}\n\n**Dava Türü:** {dava_detay['Dava Tür Adı']}")
                        with col_islem:
                            if st.button("📂 Dava Kartına Git", use_container_width=True, key=f"git_{secilen_dava}"):
                                st.session_state.aktif_dava_karti = secilen_dava; st.rerun()
                            if st.button("🗑️ Dava Kartını Sil", use_container_width=True, type="primary", key=f"sil_{secilen_dava}"):
                                conn = sqlite3.connect('hukuk.db'); c = conn.cursor()
                                c.execute("DELETE FROM davalar WHERE esas_no=?", (secilen_dava,))
                                c.execute("DELETE FROM durusmalar WHERE esas_no=?", (secilen_dava,))
                                c.execute("DELETE FROM evraklar WHERE esas_no=?", (secilen_dava,))
                                conn.commit(); conn.close(); st.rerun()
        else:
            st.subheader("✨ Yeni Dava Oluşturma Sihirbazı")
            st.progress(st.session_state.dava_adim / 3)
            if st.session_state.dava_adim == 1:
                secilen_tur = st.selectbox("Dava Türünü Seçiniz:", ["Alacak Davası", "Boşanma Davası", "İş Davası", "Ceza Davası"], key="d_sih_tur")
                if st.button("İleri ➡️", type="primary", key="d_ileri_1"):
                    st.session_state.gecici_dava['tur'] = secilen_tur; st.session_state.dava_adim = 2; st.rerun()
            elif st.session_state.dava_adim == 2:
                c1, c2 = st.columns(2)
                with c1:
                    secilen_esas = st.text_input("Dosya / Esas No:", key="d_sih_esas")
                    secilen_mahkeme = st.text_input("Mahkeme Adı:", key="d_sih_mah")
                    secilen_taraf = st.selectbox("Tarafımız:", ["DAVACI", "DAVALI", "SANIK", "MÜŞTEKİ"], key="d_sih_taraf")
                with c2:
                    secilen_tarih = st.date_input("Dosya Açılış Tarihi:", key="d_sih_tar")
                    secilen_durum = st.selectbox("Durum:", ["Derdest", "Karara Çıktı", "İstinafta"], key="d_sih_durum")
                    conn = sqlite3.connect('hukuk.db'); df_pers = pd.read_sql_query("SELECT ad_soyad FROM personeller", conn); conn.close()
                    avukat_listesi = df_pers["ad_soyad"].tolist() if not df_pers.empty else ["Avukat Yok"]
                    secilen_avukat = st.selectbox("Sorumlu Avukat Ataması:", avukat_listesi, key="d_sih_avu")
                c_g, c_i = st.columns([1, 8])
                if c_g.button("⬅️ Geri", key="d_geri_2"): st.session_state.dava_adim = 1; st.rerun()
                if c_i.button("İleri ➡️", type="primary", key="d_ileri_2"):
                    st.session_state.gecici_dava.update({'esas': secilen_esas, 'mahkeme': secilen_mahkeme, 'taraf': secilen_taraf, 'tarih': secilen_tarih, 'durum': secilen_durum, 'avukat': secilen_avukat})
                    st.session_state.dava_adim = 3; st.rerun()
            elif st.session_state.dava_adim == 3:
                st.success("Bilgiler kaydedilmeye hazır.")
                c_g, c_i = st.columns([1, 8])
                if c_g.button("⬅️ Geri", key="d_geri_3"): st.session_state.dava_adim = 2; st.rerun()
                if c_i.button("✅ Dava Kartını Kaydet", type="primary", key="d_kaydet_son"):
                    tarih_str = st.session_state.gecici_dava.get('tarih', datetime.date.today()).strftime("%d.%m.%Y")
                    conn = sqlite3.connect('hukuk.db'); c = conn.cursor()
                    c.execute("INSERT INTO davalar (esas_no, mahkeme, tur, tarih, taraf, durum, avukat) VALUES (?, ?, ?, ?, ?, ?, ?)",
                              (st.session_state.gecici_dava.get('esas', '-'), st.session_state.gecici_dava.get('mahkeme', '-'),
                               st.session_state.gecici_dava.get('tur', '-'), tarih_str, st.session_state.gecici_dava.get('taraf', '-'),
                               st.session_state.gecici_dava.get('durum', '-'), st.session_state.gecici_dava.get('avukat', '-')))
                    conn.commit(); conn.close()
                    st.session_state.dava_sihirbaz = False; st.session_state.dava_adim = 1; st.session_state.gecici_dava = {}; st.rerun()
            st.markdown("---")
            if st.button("❌ İptal Et", key="dava_iptal"): st.session_state.dava_sihirbaz = False; st.rerun()

# ==========================================
# DİĞER SEKMELER (Büro, Finans, Vekalet, Rapor, Hesap)
# ==========================================
with tab_buro:
    st.subheader("🏢 Büro Yönetimi & Görev Takibi")
    conn = sqlite3.connect('hukuk.db')
    df_personel = pd.read_sql_query("SELECT ad_soyad as 'Ad Soyad', gorev as 'Görevi', telefon as 'Telefon' FROM personeller", conn)
    df_gorev = pd.read_sql_query("SELECT id, gorev_adi, sorumlu, son_tarih, durum FROM gorevler WHERE durum='Bekliyor'", conn)
    conn.close()
    col_pers, col_gorev = st.columns([4, 6])
    with col_pers:
        st.markdown("#### 👥 Ekibimiz")
        st.dataframe(df_personel, use_container_width=True, hide_index=True)
        with st.expander("➕ Personel Ekle/Sil"):
            p_ad = st.text_input("Ad Soyad:", key="p_ad")
            p_gorev = st.text_input("Görevi:", key="p_gor")
            p_tel = st.text_input("Telefon:", key="p_tel")
            if st.button("Kaydet", type="primary", key="p_kaydet"):
                if p_ad:
                    conn = sqlite3.connect('hukuk.db'); c = conn.cursor()
                    c.execute("INSERT INTO personeller (ad_soyad, gorev, telefon) VALUES (?, ?, ?)", (p_ad, p_gorev, p_tel))
                    conn.commit(); conn.close(); st.rerun()
            st.markdown("---")
            if not df_personel.empty:
                silinecek = st.selectbox("Personel Sil:", df_personel["Ad Soyad"].tolist(), key="p_sil")
                if st.button("Sil", key="p_btn_sil"):
                    conn = sqlite3.connect('hukuk.db'); c = conn.cursor()
                    c.execute("DELETE FROM personeller WHERE ad_soyad=?", (silinecek,)); conn.commit(); conn.close(); st.rerun()
    with col_gorev:
        st.markdown("#### ✅ Bekleyen Görevler")
        if df_gorev.empty: st.success("Harika! Bekleyen görev yok.")
        else:
            for index, row in df_gorev.iterrows():
                cg1, cg2, cg3 = st.columns([6, 3, 1])
                cg1.write(f"📌 **{row['gorev_adi']}**\n*(Sorumlu: {row['sorumlu']})*")
                cg2.write(f"⏳ {row['son_tarih']}")
                if cg3.button("✔", key=f"tamamla_{row['id']}"):
                    conn = sqlite3.connect('hukuk.db'); c = conn.cursor()
                    c.execute("UPDATE gorevler SET durum='Tamamlandı' WHERE id=?", (row['id'],)); conn.commit(); conn.close(); st.rerun()
        with st.expander("➕ Yeni Görev Ata"):
            g_adi = st.text_input("Görev Açıklaması:", key="g_adi")
            g_sorumlu = st.selectbox("Sorumlu Kişi:", df_personel["Ad Soyad"].tolist() if not df_personel.empty else ["Kimse Yok"], key="g_sorumlu")
            g_tarih = st.date_input("Son Teslim Tarihi:", key="g_tarih")
            if st.button("Görevi Ata", type="primary", key="g_ata"):
                if g_adi:
                    conn = sqlite3.connect('hukuk.db'); c = conn.cursor()
                    c.execute("INSERT INTO gorevler (gorev_adi, sorumlu, son_tarih, durum) VALUES (?, ?, ?, ?)", (g_adi, g_sorumlu, g_tarih.strftime("%d.%m.%Y"), "Bekliyor"))
                    conn.commit(); conn.close(); st.rerun()

with tab_finans:
    st.subheader("💰 Finans ve Kasa Takibi")
    conn = sqlite3.connect('hukuk.db')
    df_finans = pd.read_sql_query("SELECT id, islem_turu as 'Tür', miktar as 'Tutar (₺)', aciklama as 'Açıklama', tarih as 'Tarih' FROM finans ORDER BY id DESC", conn)
    conn.close()
    cf1, cf2 = st.columns([3, 7])
    with cf1:
        st.markdown("#### 📝 Yeni İşlem")
        with st.form("finans_form", clear_on_submit=True):
            f_tur = st.radio("İşlem Türü:", ["Gelir", "Gider"])
            f_miktar = st.number_input("Tutar (₺):", min_value=0.0, step=100.0)
            f_aciklama = st.text_input("Açıklama:")
            f_tarih = st.date_input("Tarih:")
            f_kaydet = st.form_submit_button("Kayıt Ekle")
            if f_kaydet and f_miktar > 0 and f_aciklama:
                conn = sqlite3.connect('hukuk.db'); c = conn.cursor()
                c.execute("INSERT INTO finans (islem_turu, miktar, aciklama, tarih) VALUES (?, ?, ?, ?)", (f_tur, f_miktar, f_aciklama, f_tarih.strftime("%d.%m.%Y")))
                conn.commit(); conn.close(); st.rerun()
    with cf2:
        st.markdown("#### 📜 Hareketler")
        if df_finans.empty: st.info("Kayıt bulunmuyor.")
        else:
            st.dataframe(df_finans.drop(columns=['id']), use_container_width=True, hide_index=True)
            with st.expander("🗑️ İşlem Sil"):
                sil_islem = st.selectbox("Kayıt Seç:", df_finans['Açıklama'].tolist())
                if st.button("Sil", type="primary"):
                    conn = sqlite3.connect('hukuk.db'); c = conn.cursor()
                    c.execute("DELETE FROM finans WHERE aciklama=?", (sil_islem,)); conn.commit(); conn.close(); st.rerun()

with tab_vekalet:
    conn = sqlite3.connect('hukuk.db')
    df_vekalet = pd.read_sql_query("SELECT id, v_no as 'Vekalet No', muvekkil as 'Müvekkil', n_adi as 'Noter Adı', y_no as 'Yevmiye No', n_tarih as 'Tarih', durum as 'Durum' FROM vekaletler", conn)
    conn.close()
    if not st.session_state.vek_sihirbaz:
        c1, c2 = st.columns([8, 2])
        with c1: st.subheader("Vekalet Yönetimi")
        with c2:
            if st.button("➕ Yeni Vekalet", type="primary", use_container_width=True, key="btn_vek_ac"):
                st.session_state.vek_sihirbaz = True; st.session_state.vek_adim = 1; st.rerun()
        st.dataframe(df_vekalet.drop(columns=['id']), use_container_width=True, hide_index=True)
    else:
        st.subheader("📜 Yeni Vekalet")
        if st.session_state.vek_adim == 1:
            c1, c2 = st.columns(2)
            v_no = c1.text_input("Vekalet No:", key="v_sih_no")
            y_no = c1.text_input("Yevmiye No:", key="v_sih_yev")
            n_adi = c2.text_input("Noter Adı:", key="v_sih_noter")
            n_tarih = c2.date_input("Noter Tarihi:", key="v_sih_tar")
            if st.button("İleri ➡️", type="primary", key="v_ileri_1"):
                st.session_state.gecici_vekalet.update({'v_no': v_no, 'y_no': y_no, 'n_adi': n_adi, 'n_tarih': n_tarih})
                st.session_state.vek_adim = 2; st.rerun()
        elif st.session_state.vek_adim == 2:
            muvekkil = st.text_input("Müvekkil:", key="v_sih_muv")
            if st.button("✅ Kaydet", type="primary", key="v_kaydet_son"):
                conn = sqlite3.connect('hukuk.db'); c = conn.cursor()
                c.execute("INSERT INTO vekaletler (v_no, muvekkil, n_adi, y_no, n_tarih, durum) VALUES (?, ?, ?, ?, ?, ?)",
                          (st.session_state.gecici_vekalet.get('v_no'), muvekkil, st.session_state.gecici_vekalet.get('n_adi'), st.session_state.gecici_vekalet.get('y_no'), st.session_state.gecici_vekalet.get('n_tarih').strftime("%d.%m.%Y"), "Aktif"))
                conn.commit(); conn.close(); st.session_state.vek_sihirbaz = False; st.rerun()
        if st.button("❌ İptal", key="vek_iptal"): st.session_state.vek_sihirbaz = False; st.rerun()

with tab_rapor:
    conn = sqlite3.connect('hukuk.db')
    df_rapor = pd.read_sql_query("SELECT id, isim as 'Rapor İsmi', tarih as 'Tarih', durum as 'Durum' FROM raporlar", conn)
    conn.close()
    if not st.session_state.rap_sihirbaz:
        c1, c2 = st.columns([8, 2])
        with c1: st.subheader("Rapor Yönetimi")
        with c2:
            if st.button("➕ Yeni Rapor Üret", type="primary", use_container_width=True, key="btn_rap_ac"):
                st.session_state.rap_sihirbaz = True; st.session_state.rap_adim = 1; st.rerun()
        st.dataframe(df_rapor.drop(columns=['id']), use_container_width=True, hide_index=True)
    else:
        st.subheader("📊 Yeni Rapor")
        if st.session_state.rap_adim == 1:
            rap_isim = st.text_input("Raporun İsmi:", key="r_sih_isim")
            rap_turu = st.selectbox("Rapor Türü:", ["Dava Özeti", "Finansal Rapor"], key="r_sih_tur")
            if st.button("İleri ➡️", type="primary", key="r_ileri_1"):
                st.session_state.gecici_rapor.update({'isim': rap_isim, 'tur': rap_turu}); st.session_state.rap_adim = 2; st.rerun()
        elif st.session_state.rap_adim == 2:
            st.write(f"**Rapor:** {st.session_state.gecici_rapor.get('isim')}")
            if st.button("✅ Kaydet", type="primary", key="r_kaydet_son"):
                conn = sqlite3.connect('hukuk.db'); c = conn.cursor()
                c.execute("INSERT INTO raporlar (isim, tarih, durum) VALUES (?, ?, ?)", (st.session_state.gecici_rapor.get('isim'), datetime.date.today().strftime("%d.%m.%Y"), "Hazır"))
                conn.commit(); conn.close(); st.session_state.rap_sihirbaz = False; st.rerun()
        if st.button("❌ İptal", key="rap_iptal"): st.session_state.rap_sihirbaz = False; st.rerun()

with tab_hesap:
    st.subheader("🧮 Hesaplar Yönetimi")
    st.markdown("---")
    col_sol_menu, col_sag_icerik = st.columns([2, 8])
    with col_sol_menu:
        if st.button("⚖️ Dava Gideri", use_container_width=True, type="primary" if st.session_state.hesap_modu == "dava_gideri" else "secondary", key="menu_h1"):
            st.session_state.hesap_modu = "dava_gideri"; st.rerun()
        if st.button("💰 Faiz", use_container_width=True, type="primary" if st.session_state.hesap_modu == "faiz" else "secondary", key="menu_h2"):
            st.session_state.hesap_modu = "faiz"; st.rerun()
        if st.button("🧾 Makbuz", use_container_width=True, type="primary" if st.session_state.hesap_modu == "makbuz" else "secondary", key="menu_h3"):
            st.session_state.hesap_modu = "makbuz"; st.rerun()
    with col_sag_icerik:
        if st.session_state.hesap_modu == "dava_gideri":
            c_girdi, c_sonuc = st.columns(2)
            with c_girdi:
                yil = st.selectbox("Yıl:", ["2026", "2025"], key="h1_yil")
                tutar = st.number_input("Dava Tutarı (TL):", min_value=0.0, value=None, step=100.0, key="h1_tutar")
                taraf = st.number_input("Taraf Sayısı:", min_value=1, value=None, step=1, key="h1_taraf")
                if st.button("🖩 Hesapla", type="primary", key="btn_hesap_1"):
                    if tutar is not None and taraf is not None:
                        basvuru = 732.00 if yil == "2026" else 420.00
                        tebligat = taraf * 140.00
                        nispi = tutar * 0.06831 / 4
                        with c_sonuc:
                            st.info(f"**Başvuru:** {basvuru:,.2f} ₺")
                            st.info(f"**Tebligat:** {tebligat:,.2f} ₺")
                            st.warning(f"**Peşin Harç:** {nispi:,.2f} ₺")
                            st.success(f"**TOPLAM:** {(basvuru+tebligat+nispi):,.2f} ₺")
        elif st.session_state.hesap_modu == "faiz":
            c_girdi, c_sonuc = st.columns(2)
            with c_girdi:
                asil = st.number_input("Asıl Alacak (TL):", value=None, key="h2_asil")
                oran = st.number_input("Yıllık Oran (%):", value=9.0, key="h2_oran")
                b_tarih = st.date_input("Başlangıç:", key="h2_b_tar")
                s_tarih = st.date_input("Bitiş:", value=datetime.date.today(), key="h2_s_tar")
                if st.button("🖩 Hesapla", type="primary", key="btn_hesap_2"):
                    if asil is not None:
                        gun = (s_tarih - b_tarih).days
                        if gun >= 0:
                            faiz_tutar = (asil * oran * gun) / 36500
                            with c_sonuc:
                                st.warning(f"**İşleyen Faiz:** {faiz_tutar:,.2f} ₺")
                                st.success(f"**TOPLAM:** {(asil+faiz_tutar):,.2f} ₺")
        elif st.session_state.hesap_modu == "makbuz":
            c_girdi, c_sonuc = st.columns(2)
            with c_girdi:
                brut = st.number_input("Brüt Ücret (TL):", value=None, key="h3_brut")
                stopaj_orani = st.selectbox("Stopaj:", ["%20", "%0"], key="h3_stopaj")
                kdv_orani = st.selectbox("KDV:", ["%20", "%10", "%0"], key="h3_kdv")
                if st.button("🖩 Hesapla", type="primary", key="btn_hesap_3"):
                    if brut is not None:
                        stopaj = brut * (0.20 if stopaj_orani == "%20" else 0.0)
                        kdv = brut * (0.20 if kdv_orani == "%20" else (0.10 if kdv_orani == "%10" else 0.0))
                        with c_sonuc:
                            st.write(f"**Brüt:** {brut:,.2f} ₺")
                            st.error(f"**Stopaj (-):** {stopaj:,.2f} ₺")
                            st.info(f"**KDV (+):** {kdv:,.2f} ₺")
                            st.success(f"**NET ALINAN:** {(brut - stopaj + kdv):,.2f} ₺")