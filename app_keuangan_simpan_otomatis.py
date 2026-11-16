
import streamlit as st
import pandas as pd
import sqlite3
import os
from pathlib import Path
from datetime import date

# ==========================================
# KONFIGURASI
# ==========================================

st.set_page_config(
    page_title="My Finance Dashboard",
    page_icon="💰",
    layout="wide"
)

st.title("💰 My Finance Dashboard")

# Di hosting, arahkan ke folder disk permanen.
# Jika tidak ada environment variable, gunakan folder script.
DB_PATH = Path(
    os.environ.get(
        "FINANCE_DB_PATH",
        str(Path(__file__).resolve().parent / "keuangan.db")
    )
).expanduser().resolve()

DB_PATH.parent.mkdir(parents=True, exist_ok=True)


# ==========================================
# KONEKSI SQLITE
# ==========================================

def get_connection():
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


# ==========================================
# MEMBUAT DATABASE
# ==========================================

def create_database():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT,
            jenis TEXT,
            keterangan TEXT,
            kategori TEXT,
            jumlah REAL DEFAULT 0,
            satuan TEXT,
            harga REAL DEFAULT 0,
            diskon REAL DEFAULT 0,
            total REAL DEFAULT 0,
            catatan TEXT
        )
    """)

    columns = [
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(transaksi)"
        ).fetchall()
    ]

    if "diskon" not in columns:
        conn.execute("""
            ALTER TABLE transaksi
            ADD COLUMN diskon REAL DEFAULT 0
        """)

    conn.commit()
    conn.close()


create_database()


# ==========================================
# TAMBAH TRANSAKSI
# ==========================================

def tambah_transaksi(
    tanggal,
    jenis,
    keterangan,
    kategori,
    jumlah,
    satuan,
    harga,
    diskon,
    catatan
):
    subtotal = float(jumlah) * float(harga)
    total = subtotal - float(diskon)

    if total < 0:
        raise ValueError("Diskon tidak boleh melebihi subtotal.")

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
        float(jumlah),
        satuan,
        float(harga),
        float(diskon),
        float(total),
        catatan
    ))

    conn.commit()
    conn.close()


# ==========================================
# AMBIL DATA
# ==========================================

def ambil_data():
    conn = get_connection()

    df = pd.read_sql_query("""
        SELECT *
        FROM transaksi
        ORDER BY tanggal DESC, id DESC
    """, conn)

    conn.close()
    return df


# ==========================================
# HAPUS TRANSAKSI
# ==========================================

def hapus_transaksi(id_transaksi):
    conn = get_connection()

    conn.execute(
        "DELETE FROM transaksi WHERE id = ?",
        (int(id_transaksi),)
    )

    conn.commit()
    conn.close()


# ==========================================
# FORMAT RUPIAH
# ==========================================

def rupiah(nilai):
    return "Rp {:,.0f}".format(
        float(nilai)
    ).replace(",", ".")


# ==========================================
# MENU
# ==========================================

menu = st.sidebar.radio(
    "Menu",
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
# DASHBOARD
# ==========================================

if menu == "Dashboard":

    st.subheader("Ringkasan Keuangan")

    pemasukan = df.loc[
        df["jenis"] == "Pemasukan", "total"
    ].sum()

    pembelian = df.loc[
        df["jenis"] == "Pembelian", "total"
    ].sum()

    pengeluaran = df.loc[
        df["jenis"] == "Pengeluaran Belanja", "total"
    ].sum()

    saldo = pemasukan - pembelian - pengeluaran

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Pemasukan", rupiah(pemasukan))
    c2.metric("Pembelian", rupiah(pembelian))
    c3.metric("Pengeluaran", rupiah(pengeluaran))
    c4.metric("Saldo", rupiah(saldo))

    st.divider()
    st.subheader("Transaksi Terbaru")

    if not df.empty:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Belum ada transaksi.")


# ==========================================
# FORM TRANSAKSI
# ==========================================

elif menu in [
    "Pembelian",
    "Pemasukan",
    "Pengeluaran Belanja"
]:

    st.subheader("Input " + menu)

    with st.form("form_transaksi", clear_on_submit=True):

        tanggal = st.date_input(
            "Tanggal",
            value=date.today()
        )

        keterangan = st.text_input("Keterangan")

        if menu == "Pembelian":
            kategori_list = [
                "Bahan Baku", "Perlengkapan",
                "Operasional", "Lainnya"
            ]
        elif menu == "Pemasukan":
            kategori_list = [
                "Penjualan", "Modal",
                "Pendapatan Lainnya"
            ]
        else:
            kategori_list = [
                "Kebutuhan", "Transportasi",
                "Makan", "Operasional", "Lainnya"
            ]

        kategori = st.selectbox(
            "Kategori",
            kategori_list
        )

        col1, col2 = st.columns(2)

        with col1:
            jumlah = st.number_input(
                "Jumlah",
                min_value=0.0,
                step=1.0
            )

            satuan = st.text_input(
                "Satuan",
                value="Pcs"
            )

        with col2:
            harga = st.number_input(
                "Harga Satuan (Rp)",
                min_value=0.0,
                step=1000.0
            )

            diskon = 0.0

            if menu == "Pembelian":
                diskon = st.number_input(
                    "Diskon (Rp)",
                    min_value=0.0,
                    step=1000.0
                )

        catatan = st.text_area("Catatan")

        subtotal = jumlah * harga
        total = subtotal - diskon

        st.write("Subtotal:", rupiah(subtotal))
        st.write("Diskon:", rupiah(diskon))
        st.write("**Total:**", rupiah(total))

        simpan = st.form_submit_button(
            "Simpan Transaksi",
            use_container_width=True
        )

        if simpan:
            if not keterangan.strip():
                st.error("Keterangan wajib diisi.")
            elif jumlah <= 0:
                st.error("Jumlah harus lebih dari 0.")
            elif diskon > subtotal:
                st.error("Diskon tidak boleh melebihi subtotal.")
            else:
                try:
                    tambah_transaksi(
                        tanggal,
                        menu,
                        keterangan,
                        kategori,
                        jumlah,
                        satuan,
                        harga,
                        diskon,
                        catatan
                    )

                    st.success("Transaksi berhasil disimpan.")
                    st.rerun()

                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")


# ==========================================
# RIWAYAT TRANSAKSI
# ==========================================

elif menu == "Riwayat Transaksi":

    st.subheader("Riwayat Transaksi")

    if df.empty:
        st.info("Belum ada riwayat transaksi.")

    else:
        jenis = st.selectbox(
            "Filter Transaksi",
            [
                "Semua",
                "Pembelian",
                "Pemasukan",
                "Pengeluaran Belanja"
            ]
        )

        tampil = df.copy()

        if jenis != "Semua":
            tampil = tampil[
                tampil["jenis"] == jenis
            ]

        st.dataframe(
            tampil,
            use_container_width=True,
            hide_index=True
        )

        csv = tampil.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            "Download Riwayat CSV",
            data=csv,
            file_name="riwayat_keuangan.csv",
            mime="text/csv"
        )

        st.divider()

        st.subheader("Hapus Transaksi")

        id_hapus = st.selectbox(
            "Pilih ID",
            tampil["id"].tolist()
        )

        if st.button("Hapus Transaksi"):
            hapus_transaksi(id_hapus)
            st.success("Transaksi berhasil dihapus.")
            st.rerun()
