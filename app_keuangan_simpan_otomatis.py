
import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client

# ==========================================
# KONFIGURASI
# ==========================================

st.set_page_config(
    page_title="My Finance Dashboard",
    page_icon="💰",
    layout="wide"
)

st.title("💰 My Finance Dashboard")

# ==========================================
# KONEKSI DATABASE SUPABASE
# ==========================================

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

    supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )

except Exception as e:
    st.error(f"Konfigurasi Supabase belum benar: {e}")
    st.stop()


# ==========================================
# FORMAT RUPIAH
# ==========================================

def rupiah(nilai):
    nilai = float(nilai or 0)
    return "Rp " + f"{nilai:,.0f}".replace(",", ".")


# ==========================================
# MENYIMPAN TRANSAKSI
# ==========================================

def tambah_transaksi(
    tanggal,
    jenis,
    keterangan,
    kategori,
    jumlah,
    satuan,
    harga,
    total,
    catatan,
    diskon=0
):

    data = {
        "tanggal": str(tanggal),
        "jenis": jenis,
        "keterangan": keterangan,
        "kategori": kategori,
        "jumlah": float(jumlah),
        "satuan": satuan,
        "harga": float(harga),
        "diskon": float(diskon),
        "total": float(total),
        "catatan": catatan
    }

    try:
        supabase.table("transaksi").insert(
            data
        ).execute()

        return True

    except Exception as e:
        st.error(f"Gagal menyimpan transaksi: {e}")
        return False


# ==========================================
# MENGAMBIL SELURUH HISTORY
# ==========================================

def ambil_data():

    semua_data = []
    batas = 1000
    mulai = 0

    while True:

        hasil = (
            supabase.table("transaksi")
            .select("*")
            .order("tanggal", desc=True)
            .order("id", desc=True)
            .range(mulai, mulai + batas - 1)
            .execute()
        )

        data = hasil.data or []
        semua_data.extend(data)

        if len(data) < batas:
            break

        mulai += batas

    kolom = [
        "id", "tanggal", "jenis", "keterangan",
        "kategori", "jumlah", "satuan", "harga",
        "diskon", "total", "catatan"
    ]

    df = pd.DataFrame(semua_data)

    if df.empty:
        return pd.DataFrame(columns=kolom)

    for kolom_angka in [
        "jumlah", "harga", "diskon", "total"
    ]:
        df[kolom_angka] = pd.to_numeric(
            df[kolom_angka], errors="coerce"
        ).fillna(0)

    return df


# ==========================================
# MENGHAPUS TRANSAKSI
# ==========================================

def hapus_transaksi(id_transaksi):

    try:

        cek = (
            supabase.table("transaksi")
            .select("id")
            .eq("id", int(id_transaksi))
            .execute()
        )

        if not cek.data:
            return False

        (
            supabase.table("transaksi")
            .delete()
            .eq("id", int(id_transaksi))
            .execute()
        )

        return True

    except Exception as e:
        st.error(f"Gagal menghapus transaksi: {e}")
        return False


# ==========================================
# MEMBACA DATABASE
# ==========================================

try:
    df = ambil_data()

except Exception as e:
    st.error(f"Tidak dapat membaca database: {e}")
    st.stop()


# ==========================================
# SIDEBAR
# ==========================================

st.sidebar.title("💰 MY FINANCE")
st.sidebar.caption("Pencatatan keuangan harian")

st.sidebar.metric(
    "Total History",
    f"{len(df)} transaksi"
)

menu = st.sidebar.radio(
    "Pilih Menu",
    [
        "Dashboard",
        "Pembelian",
        "Pemasukan",
        "Pengeluaran Belanja",
        "Riwayat Transaksi"
    ]
)


# ==========================================
# HITUNG SALDO
# ==========================================

total_pemasukan = df.loc[
    df["jenis"] == "Pemasukan", "total"
].sum()

total_pembelian = df.loc[
    df["jenis"] == "Pembelian", "total"
].sum()

total_pengeluaran = df.loc[
    df["jenis"] == "Pengeluaran", "total"
].sum()

total_keluar = total_pembelian + total_pengeluaran
saldo = total_pemasukan - total_keluar


# ==========================================
# DASHBOARD
# ==========================================

if menu == "Dashboard":

    st.header("📊 Dashboard Keuangan")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Pemasukan",
        rupiah(total_pemasukan)
    )

    col2.metric(
        "Total Pengeluaran",
        rupiah(total_keluar)
    )

    col3.metric(
        "Saldo Saat Ini",
        rupiah(saldo)
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Rincian Pengeluaran")

        rincian = pd.DataFrame({
            "Jenis": [
                "Pembelian",
                "Pengeluaran Belanja"
            ],
            "Total": [
                total_pembelian,
                total_pengeluaran
            ]
        })

        if rincian["Total"].sum() > 0:
            st.bar_chart(
                rincian.set_index("Jenis")
            )
        else:
            st.info("Belum ada pengeluaran.")

    with col2:

        st.subheader("Komposisi Keuangan")

        komposisi = pd.DataFrame({
            "Jenis": [
                "Pemasukan",
                "Pengeluaran"
            ],
            "Total": [
                total_pemasukan,
                total_keluar
            ]
        })

        if komposisi["Total"].sum() > 0:
            st.bar_chart(
                komposisi.set_index("Jenis")
            )
        else:
            st.info("Belum ada transaksi.")

    st.divider()

    st.subheader("Transaksi Terakhir")

    if not df.empty:

        tampil = df[
            ["tanggal", "jenis", "keterangan", "total"]
        ].head(10).copy()

        tampil.columns = [
            "Tanggal", "Jenis", "Keterangan", "Total"
        ]

        tampil["Total"] = tampil["Total"].apply(rupiah)

        st.dataframe(
            tampil,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("Belum ada transaksi.")


# ==========================================
# PEMBELIAN
# ==========================================

elif menu == "Pembelian":

    st.header("🛒 Input Pembelian")

    with st.form("form_pembelian"):

        tanggal = st.date_input(
            "Tanggal Pembelian",
            value=date.today()
        )

        nama_barang = st.text_input(
            "Nama Barang",
            placeholder="Contoh: Telur, Beras, Minyak"
        )

        col1, col2 = st.columns(2)

        with col1:

            kategori = st.selectbox(
                "Kategori Barang",
                [
                    "Bahan Makanan",
                    "Sembako",
                    "Minuman",
                    "Perlengkapan Rumah",
                    "Lainnya"
                ]
            )

            jumlah = st.number_input(
                "Jumlah",
                min_value=0.0,
                value=1.0,
                step=1.0
            )

            satuan = st.selectbox(
                "Satuan",
                [
                    "Kg", "Gram", "Liter",
                    "Pcs", "Bungkus", "Dus", "Lainnya"
                ]
            )

        with col2:

            harga = st.number_input(
                "Harga per Satuan (Rp)",
                min_value=0,
                step=1000
            )

            diskon = st.number_input(
                "Diskon (Rp)",
                min_value=0,
                value=0,
                step=1000
            )

        subtotal = jumlah * harga
        total = subtotal - diskon

        st.divider()

        c1, c2, c3 = st.columns(3)

        c1.metric("Subtotal", rupiah(subtotal))
        c2.metric("Diskon", rupiah(diskon))
        c3.metric("Total Bayar", rupiah(total))

        catatan = st.text_area("Catatan (Opsional)")

        submit = st.form_submit_button(
            "Simpan Pembelian",
            use_container_width=True
        )

        if submit:

            if not nama_barang.strip():
                st.error("Nama barang harus diisi.")

            elif jumlah <= 0:
                st.error("Jumlah harus lebih dari 0.")

            elif harga <= 0:
                st.error("Harga harus lebih dari 0.")

            elif diskon > subtotal:
                st.error("Diskon melebihi subtotal.")

            else:

                berhasil = tambah_transaksi(
                    tanggal=tanggal,
                    jenis="Pembelian",
                    keterangan=nama_barang.strip(),
                    kategori=kategori,
                    jumlah=jumlah,
                    satuan=satuan,
                    harga=harga,
                    total=total,
                    catatan=catatan,
                    diskon=diskon
                )

                if berhasil:
                    st.success(
                        "Pembelian berhasil disimpan!"
                    )
                    st.rerun()


# ==========================================
# PEMASUKAN
# ==========================================

elif menu == "Pemasukan":

    st.header("💵 Input Pemasukan")

    with st.form("form_pemasukan"):

        tanggal = st.date_input(
            "Tanggal Pemasukan",
            value=date.today()
        )

        sumber = st.text_input(
            "Sumber Pemasukan",
            placeholder="Contoh: Gaji, Penjualan, Bonus"
        )

        kategori = st.selectbox(
            "Kategori",
            [
                "Gaji", "Penjualan", "Bonus",
                "Transfer", "Hadiah", "Lainnya"
            ]
        )

        jumlah = st.number_input(
            "Nominal Pemasukan (Rp)",
            min_value=0,
            step=10000
        )

        catatan = st.text_area("Catatan (Opsional)")

        submit = st.form_submit_button(
            "Simpan Pemasukan",
            use_container_width=True
        )

        if submit:

            if not sumber.strip():
                st.error("Sumber pemasukan harus diisi.")

            elif jumlah <= 0:
                st.error("Nominal harus lebih dari 0.")

            else:

                berhasil = tambah_transaksi(
                    tanggal=tanggal,
                    jenis="Pemasukan",
                    keterangan=sumber.strip(),
                    kategori=kategori,
                    jumlah=1,
                    satuan="Transaksi",
                    harga=jumlah,
                    total=jumlah,
                    catatan=catatan,
                    diskon=0
                )

                if berhasil:
                    st.success(
                        "Pemasukan berhasil disimpan!"
                    )
                    st.rerun()


# ==========================================
# PENGELUARAN BELANJA
# ==========================================

elif menu == "Pengeluaran Belanja":

    st.header("💸 Input Pengeluaran Belanja")

    with st.form("form_pengeluaran"):

        tanggal = st.date_input(
            "Tanggal Pengeluaran",
            value=date.today()
        )

        keterangan = st.text_input(
            "Keterangan Pengeluaran",
            placeholder="Contoh: Bayar listrik, Air, Transportasi"
        )

        kategori = st.selectbox(
            "Kategori Pengeluaran",
            [
                "Listrik",
                "Air",
                "Transportasi",
                "Tagihan",
                "Kesehatan",
                "Pendidikan",
                "Rumah Tangga",
                "Lainnya"
            ]
        )

        jumlah = st.number_input(
            "Nominal Pengeluaran (Rp)",
            min_value=0,
            step=10000
        )

        catatan = st.text_area("Catatan (Opsional)")

        submit = st.form_submit_button(
            "Simpan Pengeluaran",
            use_container_width=True
        )

        if submit:

            if not keterangan.strip():
                st.error("Keterangan harus diisi.")

            elif jumlah <= 0:
                st.error("Nominal harus lebih dari 0.")

            else:

                berhasil = tambah_transaksi(
                    tanggal=tanggal,
                    jenis="Pengeluaran",
                    keterangan=keterangan.strip(),
                    kategori=kategori,
                    jumlah=1,
                    satuan="Transaksi",
                    harga=jumlah,
                    total=jumlah,
                    catatan=catatan,
                    diskon=0
                )

                if berhasil:
                    st.success(
                        "Pengeluaran berhasil disimpan!"
                    )
                    st.rerun()


# ==========================================
# RIWAYAT TRANSAKSI
# ==========================================

elif menu == "Riwayat Transaksi":

    st.header("📋 Riwayat Transaksi")

    st.caption(
        "Seluruh transaksi dari hari pertama sampai hari ini."
    )

    jenis_filter = st.selectbox(
        "Filter Jenis Transaksi",
        [
            "Semua",
            "Pembelian",
            "Pemasukan",
            "Pengeluaran"
        ]
    )

    data = df.copy()

    if jenis_filter != "Semua":
        data = data[
            data["jenis"] == jenis_filter
        ]

    if not data.empty:

        data_tampil = data[
            [
                "id",
                "tanggal",
                "jenis",
                "keterangan",
                "kategori",
                "jumlah",
                "satuan",
                "harga",
                "diskon",
                "total",
                "catatan"
            ]
        ].copy()

        data_tampil.columns = [
            "ID",
            "Tanggal",
            "Jenis",
            "Keterangan",
            "Kategori",
            "Jumlah",
            "Satuan",
            "Harga Satuan",
            "Diskon",
            "Total Bayar",
            "Catatan"
        ]

        for kolom in [
            "Harga Satuan",
            "Diskon",
            "Total Bayar"
        ]:

            data_tampil[kolom] = (
                data_tampil[kolom].apply(rupiah)
            )

        st.dataframe(
            data_tampil,
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            f"Jumlah transaksi: {len(data)}"
        )

    else:

        st.info("Belum ada transaksi untuk filter ini.")

    st.divider()

    st.subheader("🗑️ Hapus Transaksi")

    id_hapus = st.number_input(
        "Masukkan ID transaksi",
        min_value=1,
        step=1
    )

    if st.button("Hapus Transaksi"):

        berhasil = hapus_transaksi(id_hapus)

        if berhasil:
            st.success("Transaksi berhasil dihapus.")
            st.rerun()
        else:
            st.warning("ID transaksi tidak ditemukan.")
