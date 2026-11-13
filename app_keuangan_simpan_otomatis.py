import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
from pathlib import Path
import shutil

# ==========================================
# KONFIGURASI APLIKASI
# ==========================================

st.set_page_config(
    page_title="My Finance Dashboard",
    page_icon="💰",
    layout="wide"
)

# Simpan database di folder yang sama dengan file script.
# Dengan path tetap ini, database tidak berpindah hanya karena
# Streamlit dijalankan dari folder kerja/terminal yang berbeda.
FOLDER_APLIKASI = Path(__file__).resolve().parent
DB_PATH = FOLDER_APLIKASI / "keuangan.db"

# Jika database lama masih berada di folder kerja terminal (cwd)
# dan belum ada di folder aplikasi, salin database lama terlebih dahulu.
# File lama tidak dihapus.
DB_LAMA = Path.cwd() / "keuangan.db"
if not DB_PATH.exists() and DB_LAMA.exists():
    if DB_LAMA.resolve() != DB_PATH.resolve():
        shutil.copy2(DB_LAMA, DB_PATH)

DB_NAME = str(DB_PATH)


# ==========================================
# DATABASE
# ==========================================

def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def create_database():
    """Membuat tabel jika belum ada dan menambahkan kolom diskon
    jika database lama belum memilikinya.
    """
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT,
            jenis TEXT,
            keterangan TEXT,
            kategori TEXT,
            jumlah REAL,
            satuan TEXT,
            harga REAL,
            total REAL,
            catatan TEXT
        )
    """)

    # Migrasi database lama: tambahkan kolom diskon tanpa menghapus data.
    columns = [
        row[1]
        for row in conn.execute("PRAGMA table_info(transaksi)").fetchall()
    ]

    if "diskon" not in columns:
        conn.execute(
            "ALTER TABLE transaksi ADD COLUMN diskon REAL DEFAULT 0"
        )

    conn.commit()
    conn.close()


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
    conn = get_connection()

    conn.execute("""
        INSERT INTO transaksi (
            tanggal, jenis, keterangan, kategori,
            jumlah, satuan, harga, diskon, total, catatan
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(tanggal),
        jenis,
        keterangan,
        kategori,
        jumlah,
        satuan,
        harga,
        diskon,
        total,
        catatan
    ))

    conn.commit()
    conn.close()


def ambil_data():
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT id, tanggal, jenis, keterangan, kategori,
               jumlah, satuan, harga, diskon, total, catatan
        FROM transaksi
        ORDER BY tanggal DESC, id DESC
        """,
        conn
    )
    conn.close()
    return df


create_database()


# ==========================================
# FORMAT RUPIAH
# ==========================================

def rupiah(nilai):
    return "Rp " + f"{nilai:,.0f}".replace(",", ".")


# ==========================================
# SIDEBAR
# ==========================================

st.sidebar.title("💰 MY FINANCE")
st.sidebar.caption("Aplikasi pencatatan keuangan harian")

# Informasi penyimpanan: membantu memastikan database yang dipakai tetap sama.
try:
    conn_info = get_connection()
    jumlah_data_tersimpan = conn_info.execute(
        "SELECT COUNT(*) FROM transaksi"
    ).fetchone()[0]
    conn_info.close()
    st.sidebar.caption(f"Data tersimpan: {jumlah_data_tersimpan} transaksi")
    st.sidebar.caption(f"Lokasi database: {DB_PATH}")
except Exception as e:
    st.sidebar.error(f"Database belum dapat dibaca: {e}")

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

df = ambil_data()


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

    st.title("📊 Dashboard Keuangan")
    st.write("Ringkasan kondisi keuangan saat ini.")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Pemasukan", rupiah(total_pemasukan))
    col2.metric("Total Pengeluaran", rupiah(total_keluar))
    col3.metric("Saldo Saat Ini", rupiah(saldo))

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Rincian Pengeluaran")

        rincian = pd.DataFrame({
            "Jenis": ["Pembelian", "Pengeluaran Belanja"],
            "Total": [total_pembelian, total_pengeluaran]
        })

        if rincian["Total"].sum() > 0:
            st.bar_chart(rincian.set_index("Jenis"))
        else:
            st.info("Belum ada pengeluaran.")

    with col2:
        st.subheader("Komposisi Keuangan")

        keuangan = pd.DataFrame({
            "Jenis": ["Pemasukan", "Pengeluaran"],
            "Total": [total_pemasukan, total_keluar]
        })

        if keuangan["Total"].sum() > 0:
            st.bar_chart(keuangan.set_index("Jenis"))
        else:
            st.info("Belum ada transaksi.")

    st.divider()
    st.subheader("Transaksi Terakhir")

    if not df.empty:
        tampil = df[
            ["tanggal", "jenis", "keterangan", "total"]
        ].head(10).copy()

        tampil.columns = ["Tanggal", "Jenis", "Keterangan", "Total"]
        tampil["Total"] = tampil["Total"].apply(rupiah)

        st.dataframe(
            tampil,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Belum ada data transaksi.")


# ==========================================
# MENU PEMBELIAN
# ==========================================

elif menu == "Pembelian":

    st.title("🛒 Input Pembelian")
    st.write("Catat barang atau kebutuhan yang dibeli.")

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
                ["Kg", "Gram", "Liter", "Pcs", "Bungkus", "Dus", "Lainnya"]
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
                step=1000,
                help="Masukkan nominal potongan harga dalam rupiah."
            )

        subtotal = jumlah * harga
        total = subtotal - diskon

        st.divider()

        ringkas1, ringkas2, ringkas3 = st.columns(3)
        ringkas1.metric("Subtotal", rupiah(subtotal))
        ringkas2.metric("Diskon", rupiah(diskon))
        ringkas3.metric("Total Bayar", rupiah(total))

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
                st.error("Diskon tidak boleh lebih besar dari subtotal.")
            else:
                tambah_transaksi(
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

                st.success(
                    f"Pembelian berhasil disimpan. Total bayar: {rupiah(total)}"
                )
                st.rerun()


# ==========================================
# MENU PEMASUKAN
# ==========================================

elif menu == "Pemasukan":

    st.title("💵 Input Pemasukan")
    st.write("Catat semua uang yang masuk.")

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
            ["Gaji", "Penjualan", "Bonus", "Transfer", "Hadiah", "Lainnya"]
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
                tambah_transaksi(
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

                st.success("Pemasukan berhasil disimpan!")
                st.rerun()


# ==========================================
# MENU PENGELUARAN BELANJA
# ==========================================

elif menu == "Pengeluaran Belanja":

    st.title("💸 Input Pengeluaran Belanja")
    st.write("Catat pengeluaran selain pembelian barang harian.")

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
                tambah_transaksi(
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

                st.success("Pengeluaran berhasil disimpan!")
                st.rerun()


# ==========================================
# RIWAYAT TRANSAKSI
# ==========================================

elif menu == "Riwayat Transaksi":

    st.title("📋 Riwayat Transaksi")
    st.write("Semua data pembelian, pemasukan, dan pengeluaran.")

    if not df.empty:

        jenis_filter = st.selectbox(
            "Filter Jenis Transaksi",
            ["Semua", "Pembelian", "Pemasukan", "Pengeluaran"]
        )

        data = df.copy()

        if jenis_filter != "Semua":
            data = data[data["jenis"] == jenis_filter]

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

        for kolom in ["Harga Satuan", "Diskon", "Total Bayar"]:
            data_tampil[kolom] = data_tampil[kolom].apply(rupiah)

        st.dataframe(
            data_tampil,
            use_container_width=True,
            hide_index=True
        )

        csv_data = data_tampil.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            "📥 Download Data CSV",
            data=csv_data,
            file_name="laporan_keuangan.csv",
            mime="text/csv"
        )

        st.divider()
        st.subheader("Hapus Transaksi")

        id_hapus = st.number_input(
            "Masukkan ID transaksi yang ingin dihapus",
            min_value=1,
            step=1
        )

        if st.button("🗑️ Hapus Transaksi"):
            conn = get_connection()

            cursor = conn.execute(
                "DELETE FROM transaksi WHERE id = ?",
                (int(id_hapus),)
            )

            conn.commit()
            berhasil = cursor.rowcount > 0
            conn.close()

            if berhasil:
                st.success("Transaksi berhasil dihapus.")
                st.rerun()
            else:
                st.error("ID transaksi tidak ditemukan.")

    else:
        st.info("Belum ada riwayat transaksi.")
