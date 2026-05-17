-- MySQL dump 10.13  Distrib 8.3.0, for macos12.6 (x86_64)
--
-- Host: 127.0.0.1    Database: care_assist
-- ------------------------------------------------------
-- Server version	8.3.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `care_assist`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `care_assist` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `care_assist`;

--
-- Table structure for table `ai_conversations`
--

DROP TABLE IF EXISTS `ai_conversations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ai_conversations` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `member_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `page_context` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `messages` json NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_ai_conv_member_updated` (`member_id`,`updated_at`),
  CONSTRAINT `ai_conversations_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `members` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `alembic_version`
--

DROP TABLE IF EXISTS `alembic_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `families`
--

DROP TABLE IF EXISTS `families`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `families` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `admin_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invite_code` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `invite_code` (`invite_code`),
  KEY `idx_invite_code` (`invite_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `health_events`
--

DROP TABLE IF EXISTS `health_events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `health_events` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `member_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `type` enum('visit','lab','medication','symptom','ai','hospital','vaccine','checkup','milestone') COLLATE utf8mb4_unicode_ci NOT NULL,
  `event_date` date NOT NULL,
  `event_time` time DEFAULT NULL,
  `hospital` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `department` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `doctor` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `diagnosis` text COLLATE utf8mb4_unicode_ci,
  `notes` text COLLATE utf8mb4_unicode_ci,
  `report_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hospital_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` enum('normal','abnormal') COLLATE utf8mb4_unicode_ci NOT NULL,
  `abnormal_count` int NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_health_event_member_date` (`member_id`,`event_date`),
  KEY `idx_health_event_type` (`type`),
  CONSTRAINT `health_events_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `members` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `hospital_events`
--

DROP TABLE IF EXISTS `hospital_events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `hospital_events` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `member_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `hospital` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `department` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `admission_date` date NOT NULL,
  `discharge_date` date DEFAULT NULL,
  `diagnosis` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `doctor` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `key_nodes` json NOT NULL,
  `watch_indicators` json NOT NULL,
  `status` enum('active','discharged') COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_hospital_member_status` (`member_id`,`status`),
  CONSTRAINT `hospital_events_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `members` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `indicator_data`
--

DROP TABLE IF EXISTS `indicator_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `indicator_data` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `member_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `indicator_key` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `indicator_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `value` decimal(10,3) NOT NULL,
  `unit` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `lower_limit` decimal(10,3) DEFAULT NULL,
  `upper_limit` decimal(10,3) DEFAULT NULL,
  `status` enum('normal','low','high','critical') COLLATE utf8mb4_unicode_ci NOT NULL,
  `deviation_percent` decimal(5,2) NOT NULL,
  `record_date` date NOT NULL,
  `record_time` time DEFAULT NULL,
  `source_report_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_hospital_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_batch_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_indicator_member_date` (`member_id`,`record_date`),
  KEY `idx_indicator_member_key_date` (`member_id`,`indicator_key`,`record_date`),
  KEY `idx_indicator_status` (`status`),
  CONSTRAINT `indicator_data_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `members` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `medication_logs`
--

DROP TABLE IF EXISTS `medication_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `medication_logs` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `medication_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `member_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `scheduled_date` date NOT NULL,
  `scheduled_time` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `taken_at` datetime DEFAULT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_medlog_medication_date` (`medication_id`,`scheduled_date`),
  KEY `idx_medlog_member_date` (`member_id`,`scheduled_date`),
  CONSTRAINT `medication_logs_ibfk_1` FOREIGN KEY (`medication_id`) REFERENCES `medications` (`id`) ON DELETE CASCADE,
  CONSTRAINT `medication_logs_ibfk_2` FOREIGN KEY (`member_id`) REFERENCES `members` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `medications`
--

DROP TABLE IF EXISTS `medications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `medications` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `member_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dosage` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `frequency` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `time_slots` json NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_medication_member_status` (`member_id`,`status`),
  CONSTRAINT `medications_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `members` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `members`
--

DROP TABLE IF EXISTS `members`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `members` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `family_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `avatar_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `birth_date` date DEFAULT NULL,
  `gender` enum('male','female') COLLATE utf8mb4_unicode_ci NOT NULL,
  `blood_type` enum('A','B','AB','O') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `allergies` json NOT NULL,
  `chronic_diseases` json NOT NULL,
  `type` enum('adult','child','elderly') COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` enum('creator','member') COLLATE utf8mb4_unicode_ci NOT NULL,
  `wx_openid` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `subscription_status` json NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_member_family` (`family_id`),
  KEY `idx_member_wx_openid` (`wx_openid`),
  CONSTRAINT `members_ibfk_1` FOREIGN KEY (`family_id`) REFERENCES `families` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `reminders`
--

DROP TABLE IF EXISTS `reminders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `reminders` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `member_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `type` enum('vaccine','checkup','review','medication') COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `scheduled_date` date NOT NULL,
  `status` enum('pending','completed','overdue') COLLATE utf8mb4_unicode_ci NOT NULL,
  `completed_date` date DEFAULT NULL,
  `related_indicator` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `related_report_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `priority` enum('critical','high','normal','low') COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_reminder_member_status` (`member_id`,`status`),
  KEY `idx_reminder_scheduled` (`scheduled_date`),
  CONSTRAINT `reminders_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `members` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `reports`
--

DROP TABLE IF EXISTS `reports`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `reports` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `member_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `type` enum('lab','diagnosis','prescription','discharge') COLLATE utf8mb4_unicode_ci NOT NULL,
  `hospital` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `department` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `report_date` date DEFAULT NULL,
  `images` json NOT NULL,
  `extracted_indicators` json DEFAULT NULL,
  `ai_summary` text COLLATE utf8mb4_unicode_ci,
  `hospital_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ocr_status` enum('pending','processing','completed','failed') COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_report_member_date` (`member_id`,`report_date`),
  CONSTRAINT `reports_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `members` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `vaccine_records`
--

DROP TABLE IF EXISTS `vaccine_records`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `vaccine_records` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `member_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `vaccine_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dose` int NOT NULL,
  `scheduled_date` date NOT NULL,
  `actual_date` date DEFAULT NULL,
  `status` enum('completed','pending','upcoming','overdue') COLLATE utf8mb4_unicode_ci NOT NULL,
  `location` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `batch_no` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reaction` text COLLATE utf8mb4_unicode_ci,
  `is_custom` tinyint(1) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_vaccine_member_status` (`member_id`,`status`),
  KEY `idx_vaccine_scheduled` (`scheduled_date`),
  CONSTRAINT `vaccine_records_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `members` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-05-17 17:45:23
