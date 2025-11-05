-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Waktu pembuatan: 19 Nov 2024 pada 21.05
-- Versi server: 10.4.32-MariaDB
-- Versi PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `pengaduan`
--

-- --------------------------------------------------------

--
-- Struktur dari tabel `aduan`
--

CREATE TABLE `aduan` (
  `id_laporan` int(11) NOT NULL,
  `judul_pengaduan` text NOT NULL,
  `kronologi` text NOT NULL,
  `bukti_foto` longblob NOT NULL,
  `bukti_file` blob NOT NULL,
  `pesan` text NOT NULL,
  `id_pelapor` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data untuk tabel `aduan`
--

INSERT INTO `aduan` (`id_laporan`, `judul_pengaduan`, `kronologi`, `bukti_foto`, `bukti_file`, `pesan`, `id_pelapor`) VALUES
(48, 'C65mUMdkpj4GPKGWpI0nqx7EDmMk4ifTN3mensiOUnQ=', 'BJ1kUWx96aGf4a9lvPIXkP7Eu16BjzQiXRqJWhDVIWs=', 0x75706c6f616465645f646174615c696d616765735c35342e706e67, 0x75706c6f616465645f646174615c66696c65735c5541535f4b6f6d6d61735f313233323230313734202831292e646f6378, '', 2),
(49, 'IsEoyeUk+mCz5UG6DJrzj3yG+h3D7I7o2mDDDQxjLkw=', 'wwTMiRHft6B/TO+gohp2k30PDPGzC4wOBG/XD1Sgr+s=', 0x75706c6f616465645f646174615c696d616765735c696d6167652e706e67, 0x75706c6f616465645f646174615c66696c65735c53656d6573746572205620555453204b524950544f47524146492e706466, '', 2),
(50, '+GdoIALiFnaddBTCu3KIZCtFXjK8V7retDFA8YoH5N4=', 'dWHq0S1TpIMhTzqiDLgrIS1POtyvnfQnXu5BFoRokE8=', 0x75706c6f616465645f646174615c696d616765735c576861747341707020496d61676520323032342d31312d31372061742032302e32322e34335f64316666326339632e6a7067, 0x75706c6f616465645f646174615c66696c65735c3132333232303137345f526f79616e204164697479615f547567617320322053697374656d204f7065726173695f49462d412e706466, 'ini gambarnya', 2),
(51, 'Mbq1kTt9DB1hMLQqotnrZOly1dfa7oAciR1YoRNkMUrqkK7C0Ar58sQJWR8J0inX', '7kF5Rh+R5YpKV8343MeZlrQbEtYcem8gEyp5NV/V2pM=', 0x75706c6f616465645f646174615c696d616765735c6b65736d612042454d204654492e706e67, 0x75706c6f616465645f646174615c66696c65735c637620726f79616e206164697479612e646f6378, 'apaya', 4),
(52, '9VtchjFQbH/492LUqwtMVYCroI4i93hSB/OR2xqXWBo=', 'u2TLNub5tj6B3xWVFITwMKLz956pOvy7pqTz2lOCUKw=', 0x75706c6f616465645f646174615c696d616765735c62616e676b69745f7669727475616c5f6261636b67726f756e645f6d6972726f722e706e67, 0x75706c6f616465645f646174615c66696c65735c526f79616e204164697479312e646f6378, '', 4);

-- --------------------------------------------------------

--
-- Struktur dari tabel `user`
--

CREATE TABLE `user` (
  `id` int(11) NOT NULL,
  `nama` varchar(255) NOT NULL,
  `username` varchar(255) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data untuk tabel `user`
--

INSERT INTO `user` (`id`, `nama`, `username`, `email`, `password`) VALUES
(2, 'indah', 'indah123', 'indah123@gmail.com', 'f3385c508ce54d577fd205a1b2ecdfb7'),
(3, 'fairul imron', 'irul', 'irul@gmail.com', 'e9b195132b4fe5201534844aafaab68c'),
(4, 'roh', 'roh', 'roh2@gmail.com', 'be7e16e1f31a293e6b3665a80a73c113'),
(5, 'affan', 'ambon', 'ambon@gmail.com', 'f54b035043726f40c0993982c82bbbfe'),
(6, 'admin', 'admin', 'admin@gmail.com', 'admin');

--
-- Indexes for dumped tables
--

--
-- Indeks untuk tabel `aduan`
--
ALTER TABLE `aduan`
  ADD PRIMARY KEY (`id_laporan`);

--
-- Indeks untuk tabel `user`
--
ALTER TABLE `user`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT untuk tabel yang dibuang
--

--
-- AUTO_INCREMENT untuk tabel `aduan`
--
ALTER TABLE `aduan`
  MODIFY `id_laporan` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=53;

--
-- AUTO_INCREMENT untuk tabel `user`
--
ALTER TABLE `user`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
