DROP TABLE IF EXISTS `anime_users`;
CREATE TABLE `anime_users` (
  `anime_title` varchar(255) NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`anime_title`,`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `favorite_music`;
CREATE TABLE `favorite_music` (
  `id` int NOT NULL AUTO_INCREMENT,
  `song` text NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `music`;
CREATE TABLE `music` (
  `guild_id` bigint NOT NULL,
  `channel_id` bigint NOT NULL,
  `message_id` bigint DEFAULT NULL,
  `queue_id` bigint DEFAULT NULL,
  `locked` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`guild_id`),
  UNIQUE KEY `guild_id` (`guild_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `valorant_crosshairs`;
CREATE TABLE `valorant_crosshairs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `label` text NOT NULL,
  `code` text NOT NULL,
  `image` blob,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `valorant_profiles`;
CREATE TABLE `valorant_profiles` (
  `user_id` bigint NOT NULL,
  `label` text NOT NULL,
  `name` text NOT NULL,
  `tag` text NOT NULL,
  PRIMARY KEY (`user_id`,`label`(32))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
