-- Adminer 4.8.1 MySQL 8.0.35 dump

SET NAMES utf8;
SET time_zone = '+00:00';
SET foreign_key_checks = 0;
SET sql_mode = 'NO_AUTO_VALUE_ON_ZERO';

SET NAMES utf8mb4;

DROP DATABASE IF EXISTS `db_parser`;
CREATE DATABASE `db_parser` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `db_parser`;

-- Таблица: parsed_data
DROP TABLE IF EXISTS parsed_data;
CREATE TABLE IF NOT EXISTS parsed_data (
	`id` int NOT NULL AUTO_INCREMENT,
	`links_from_page` VARCHAR(255) DEFAULT 'No urls from this page',
	PRIMARY KEY (id)
);

-- Таблица: site_config
DROP TABLE IF EXISTS site_config;
CREATE TABLE IF NOT EXISTS site_config (
	`id` int NOT NULL AUTO_INCREMENT,
	`index_site_link` VARCHAR(255) NOT NULL,
	`link_url_start` LONGTEXT NOT NULL,
	`upload_path_folder` VARCHAR(255) NOT NULL DEFAULT '',
	PRIMARY KEY (id)
);
