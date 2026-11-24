-- Reference schema; importer uses benchmark/schema.py as source of truth.
USE population_db;

CREATE TABLE `provinces` (`province_code` CHAR(2) NOT NULL, `province_name` VARCHAR(100) NOT NULL, PRIMARY KEY (`province_code`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE `wards` (`ward_code` CHAR(5) NOT NULL, `ward_name` VARCHAR(100) NOT NULL, `province_code` CHAR(2) NOT NULL, PRIMARY KEY (`ward_code`), KEY core_0 (province_code), FOREIGN KEY (`province_code`) REFERENCES `provinces` (`province_code`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE `households` (`household_id` BIGINT NOT NULL, `ward_code` CHAR(5) NOT NULL, `household_size` INT NOT NULL, `housing_type` VARCHAR(100) NOT NULL, `housing_tenure` VARCHAR(100) NOT NULL, `address_label` VARCHAR(40) NOT NULL, PRIMARY KEY (`household_id`), KEY core_0 (ward_code), FOREIGN KEY (`ward_code`) REFERENCES `wards` (`ward_code`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE `persons` (`person_id` BIGINT NOT NULL, `cccd` CHAR(12) NOT NULL, `last_name` VARCHAR(100) NOT NULL, `middle_name` VARCHAR(100) NOT NULL, `given_name` VARCHAR(100) NOT NULL, `full_name` VARCHAR(255) NOT NULL, `gender` VARCHAR(100) NOT NULL, `date_of_birth` DATE NOT NULL, `birth_ward_code` CHAR(5) NOT NULL, `nationality` VARCHAR(100) NOT NULL, `ethnicity` VARCHAR(100) NOT NULL, `marital_status` VARCHAR(100) NOT NULL, `education_level` VARCHAR(100) NOT NULL, `employment_status` VARCHAR(100) NOT NULL, `occupation` VARCHAR(100) NOT NULL, PRIMARY KEY (`person_id`), UNIQUE KEY uq_cccd (cccd), KEY core_0 (birth_ward_code), FOREIGN KEY (`birth_ward_code`) REFERENCES `wards` (`ward_code`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE `household_members` (`person_id` BIGINT NOT NULL, `household_id` BIGINT NOT NULL, `relationship_to_head` VARCHAR(100) NOT NULL, PRIMARY KEY (`person_id`), KEY core_0 (household_id), FOREIGN KEY (`person_id`) REFERENCES `persons` (`person_id`), FOREIGN KEY (`household_id`) REFERENCES `households` (`household_id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;

CREATE TABLE `residence_history` (`residence_id` BIGINT NOT NULL, `person_id` BIGINT NOT NULL, `ward_code` CHAR(5) NOT NULL, `residence_type` VARCHAR(100) NOT NULL, `start_date` DATE NOT NULL, `end_date` DATE NULL, `is_current` TINYINT NOT NULL, PRIMARY KEY (`residence_id`), KEY core_0 (person_id), KEY core_1 (ward_code), FOREIGN KEY (`person_id`) REFERENCES `persons` (`person_id`), FOREIGN KEY (`ward_code`) REFERENCES `wards` (`ward_code`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_bin;
