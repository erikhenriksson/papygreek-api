SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
SET character_set_connection=utf8mb4;
CREATE DATABASE IF NOT EXISTS papygreek DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

USE papygreek;

CREATE TABLE IF NOT EXISTS `user` (
    `id`           INT unsigned NOT NULL AUTO_INCREMENT,
    `email`        VARCHAR(80) NOT NULL,
    `name`         VARCHAR(80),
    `level`        INT unsigned DEFAULT NULL,
    --
    PRIMARY KEY (`id`),
    UNIQUE (`email`)
);

INSERT INTO `user` (`id`, `email`, `name`, `level`) VALUES (NULL, 'papygreek.helsinki@gmail.com', 'PapyGreek', '2');

CREATE TABLE IF NOT EXISTS `text` (
    `id`              INT unsigned NOT NULL AUTO_INCREMENT,
    `series_name`     VARCHAR(512) DEFAULT NULL,
    `series_type`     VARCHAR(80) NOT NULL,
    `name`            VARCHAR(80) NOT NULL,
    `language`        VARCHAR(80) NOT NULL,
    `xml_papygreek`   MEDIUMTEXT DEFAULT NULL,
    `xml_original`    MEDIUMTEXT DEFAULT NULL,
    `xml_next`        MEDIUMTEXT DEFAULT NULL,
    `tm`              VARCHAR(512) DEFAULT NULL,
    `hgv`             TEXT DEFAULT NULL,
    `pleiades`        VARCHAR(512) DEFAULT NULL,
    `date_not_before` VARCHAR(80) DEFAULT NULL,
    `date_not_after`  VARCHAR(80) DEFAULT NULL,
    `place_name`      VARCHAR(512) DEFAULT NULL,
    `tokenized`       TIMESTAMP DEFAULT NOW(),
    `checked`         TIMESTAMP DEFAULT NOW(),
    `orig_status`     TINYINT unsigned DEFAULT 0 NOT NULL,
    `reg_status`      TINYINT unsigned DEFAULT 0 NOT NULL,
    `current`         TINYINT unsigned DEFAULT 1 NOT NULL,
    `v1`              TINYINT unsigned DEFAULT 0 NOT NULL,
    --
    PRIMARY KEY (`id`),
    UNIQUE (`name`, `series_name`),
    KEY (`date_not_before`),
    KEY (`date_not_after`),
    KEY (`place_name`(127)),
    KEY (`tm`),
    KEY (`name`),
    KEY (`language`),
    KEY (`series_name`),
    KEY (`series_type`),
    KEY (`orig_status`),
    KEY (`reg_status`),
    KEY (`orig_status`, `reg_status`),
    KEY (`current`),
    KEY (`series_type`, `series_name`)
);

CREATE TABLE IF NOT EXISTS `treebank_backup` (
    `id`           INT unsigned NOT NULL AUTO_INCREMENT,
    `text_id`      INT unsigned NOT NULL,
    `treebank_xml` MEDIUMTEXT DEFAULT NULL,
    `created`      TIMESTAMP DEFAULT NOW(),
    --
    PRIMARY KEY (`id`),
    KEY (`text_id`),
    FOREIGN KEY (`text_id`) REFERENCES `text` (`id`)
);

CREATE TABLE IF NOT EXISTS `token` (
    `id`            INT unsigned NOT NULL AUTO_INCREMENT,
    `text_id`       INT unsigned NOT NULL,
    `n`             INT unsigned NOT NULL,
    `sentence_n`    INT unsigned NOT NULL,
    `line`          VARCHAR(80),
    `line_rend`     VARCHAR(80),
    `hand`          VARCHAR(80),
    `textpart`      VARCHAR(1024),
    `aow_n`         SMALLINT unsigned,

    `orig_form`     VARCHAR(512),
    `orig_plain`    VARCHAR(512),
    `orig_flag`     VARCHAR(80),
    `orig_app_type` VARCHAR(512),
    `orig_num`      VARCHAR(512),
    `orig_num_rend` VARCHAR(512),
    `orig_lang`     VARCHAR(512),
    `orig_info`     TEXT,
    `orig_lemma`    VARCHAR(80),
    `orig_lemma_plain`    VARCHAR(80),
    `orig_postag`   VARCHAR(80),
    `orig_relation` VARCHAR(80),
    `orig_head`     VARCHAR(80),

    `reg_form`     VARCHAR(512),
    `reg_plain`    VARCHAR(512),
    `reg_flag`     VARCHAR(80),
    `reg_app_type` VARCHAR(512),
    `reg_num`      VARCHAR(512),
    `reg_num_rend` VARCHAR(512),
    `reg_lang`     VARCHAR(512),
    `reg_info`     TEXT,
    `reg_lemma`    VARCHAR(80),
    `reg_lemma_plain`    VARCHAR(80),
    `reg_postag`   VARCHAR(80),
    `reg_relation` VARCHAR(80),
    `reg_head`     VARCHAR(80),

    `insertion_id` VARCHAR(80),
    `artificial`   VARCHAR(80),
    `pending_deletion`   SMALLINT unsigned,
    --
    PRIMARY KEY (`id`),
    KEY (`text_id`),
    KEY (`n`),
    KEY (`sentence_n`),
    KEY (`hand`),
    KEY (`aow_n`),

    KEY (`orig_form`(80)),
    KEY (`orig_plain`(80)),
    KEY (`orig_flag`(80)),
    KEY (`orig_lang`(80)),
    KEY (`orig_lemma`(80)),
    KEY (`orig_lemma_plain`(80)),
    KEY (`orig_postag`(80)),
    KEY (`orig_relation`(80)),
    KEY (`orig_head`(80)),
    KEY (`orig_app_type`(80)),

    KEY (`reg_form`(80)),
    KEY (`reg_plain`(80)),
    KEY (`reg_flag`(80)),
    KEY (`reg_lang`(80)),
    KEY (`reg_lemma`(80)),
    KEY (`reg_lemma_plain`(80)),
    KEY (`reg_postag`(80)),
    KEY (`reg_relation`(80)),
    KEY (`reg_head`(80)),
    KEY (`reg_app_type`(80)),

    KEY (`insertion_id`(80)),
    KEY (`artificial`(80)),

    KEY (`pending_deletion`),

    UNIQUE (`n`, `sentence_n`, `text_id`, `pending_deletion`),
    FOREIGN KEY (`text_id`) REFERENCES `text` (`id`)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS `token_rdg` (
    `id`       INT unsigned NOT NULL AUTO_INCREMENT,
    `token_id` INT unsigned NOT NULL,
    `form`     VARCHAR(512),
    `plain`    VARCHAR(512),
    `flag`     VARCHAR(80),
    `app_type` VARCHAR(512),
    `num`      VARCHAR(512),
    `num_rend` VARCHAR(512),
    `lang`     VARCHAR(512),
    `info`     TEXT,
    --
    PRIMARY KEY (`id`),
    KEY (`form`(80)),
    KEY (`plain`(80)),
    KEY (`flag`(80)),
    KEY (`lang`(80)),
    KEY (`app_type`(80)),
    KEY (`token_id`),
    FOREIGN KEY (`token_id`) REFERENCES `token` (`id`)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS `token_v1` (
    `id`            INT unsigned NOT NULL AUTO_INCREMENT,
    `text_id`       INT unsigned NOT NULL,
    `n`             INT unsigned NOT NULL,
    `sentence_n`    INT unsigned NOT NULL,
    `line`          VARCHAR(80),
    `line_rend`     VARCHAR(80),
    `hand`          VARCHAR(80),
    `textpart`      VARCHAR(1024),
    `aow_n`         SMALLINT,

    `orig_form`     VARCHAR(512),
    `orig_plain`    VARCHAR(512),
    `orig_flag`     VARCHAR(80),
    `orig_app_type` VARCHAR(512),
    `orig_num`      VARCHAR(512),
    `orig_num_rend` VARCHAR(512),
    `orig_lang`     VARCHAR(512),
    `orig_info`     TEXT,
    `orig_lemma`    VARCHAR(80),
    `orig_postag`   VARCHAR(80),
    `orig_relation` VARCHAR(80),
    `orig_head`     VARCHAR(80),

    `reg_form`     VARCHAR(512),
    `reg_plain`    VARCHAR(512),
    `reg_flag`     VARCHAR(80),
    `reg_app_type` VARCHAR(512),
    `reg_num`      VARCHAR(512),
    `reg_num_rend` VARCHAR(512),
    `reg_lang`     VARCHAR(512),
    `reg_info`     TEXT,
    `reg_lemma`    VARCHAR(80),
    `reg_postag`   VARCHAR(80),
    `reg_relation` VARCHAR(80),
    `reg_head`     VARCHAR(80),

    `insertion_id` VARCHAR(80),
    `artificial`   VARCHAR(80),
    --
    PRIMARY KEY (`id`),
    KEY (`text_id`),
    KEY (`n`),
    KEY (`sentence_n`),
    KEY (`hand`),
    KEY (`aow_n`),

    KEY (`orig_form`(80)),
    KEY (`orig_plain`(80)),
    KEY (`orig_flag`(80)),
    KEY (`orig_lang`(80)),
    KEY (`orig_lemma`(80)),
    KEY (`orig_postag`(80)),
    KEY (`orig_relation`(80)),
    KEY (`orig_head`(80)),
    KEY (`orig_app_type`(80)),

    KEY (`reg_form`(80)),
    KEY (`reg_plain`(80)),
    KEY (`reg_flag`(80)),
    KEY (`reg_lang`(80)),
    KEY (`reg_lemma`(80)),
    KEY (`reg_postag`(80)),
    KEY (`reg_relation`(80)),
    KEY (`reg_head`(80)),
    KEY (`reg_app_type`(80)),

    KEY (`insertion_id`(80)),
    KEY (`artificial`(80)),

    UNIQUE (`n`, `sentence_n`, `text_id`),
    FOREIGN KEY (`text_id`) REFERENCES `text` (`id`)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS `token_closure` (
    `text_id`     INT unsigned NOT NULL,
    `ancestor`    INT unsigned NOT NULL,
    `descendant`  INT unsigned NOT NULL,
    `n`           INT unsigned NOT NULL,
    `depth`       TINYINT NOT NULL,
    `layer`       VARCHAR(80),
    --
    KEY (`text_id`),
    KEY (`ancestor`),
    KEY (`descendant`),
    KEY (`n`),
    KEY (`depth`),
    KEY (`layer`),
    UNIQUE (`ancestor`, `descendant`, `depth`, `layer`, `n`),
    FOREIGN KEY (`text_id`) REFERENCES `text` (`id`)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS `comment` (
    `id`          INT unsigned NOT NULL AUTO_INCREMENT,
    `text_id`     INT unsigned NOT NULL,
    `user_id`     INT unsigned NOT NULL,
    `text`        MEDIUMTEXT,
    `type`        TINYINT unsigned,
    `layer`       VARCHAR(80),
    `created`     TIMESTAMP DEFAULT NOW(),
    --
    PRIMARY KEY (`id`),
    KEY (`user_id`, `text_id`),
    KEY (`text_id`),
    FOREIGN KEY (`text_id`) REFERENCES `text` (`id`)
        ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
);

CREATE TABLE IF NOT EXISTS `person` (
    `id`                  INT unsigned NOT NULL AUTO_INCREMENT,
    `tm_id`               INT unsigned,
    `name`                VARCHAR(512),
    `gender`              VARCHAR(80),
    --
    PRIMARY KEY (`id`),
    KEY(`name`(80)),
    KEY(`gender`),
    KEY(`tm_id`)
);

CREATE TABLE IF NOT EXISTS `aow_text_type` (
    `id`                  INT unsigned NOT NULL AUTO_INCREMENT,
    `text_id`             INT unsigned NOT NULL,
    `aow_n`               TINYINT unsigned NOT NULL,
    `text_type`           VARCHAR(80),
    `hypercategory`       TINYINT unsigned NOT NULL DEFAULT 0,
    `category`            TINYINT unsigned NOT NULL DEFAULT 0,
    `subcategory`         TINYINT unsigned NOT NULL DEFAULT 0,
    `status`              TINYINT unsigned NOT NULL DEFAULT 0,
    --
    PRIMARY KEY (`id`),
    UNIQUE (`text_id`, `aow_n`, `hypercategory`, `category`, `subcategory`),
    KEY (`text_type`),
    KEY (`category`),
    KEY (`hypercategory`),
    KEY (`subcategory`),
    KEY (`text_id`),
    FOREIGN KEY (`text_id`) REFERENCES `text` (`id`)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS `aow_person` (
    `id`                  INT unsigned NOT NULL AUTO_INCREMENT,
    `text_id`             INT unsigned NOT NULL,
    `aow_n`               TINYINT unsigned NOT NULL,
    `person_id`           INT unsigned,
    `role`                VARCHAR(80),
    `uncertain`           TINYINT unsigned,
    `handwriting`         TEXT,
    `honorific`           TEXT,
    `ethnic`              TEXT,
    `occupation`          TEXT,
    `domicile`            TEXT,
    `age`                 TEXT,
    `education`           TEXT,
    --
    PRIMARY KEY (`id`),
    KEY (`role`),
    KEY (`uncertain`),
    KEY (`handwriting`(100)),
    KEY (`honorific`(100)),
    KEY (`ethnic`(100)),
    KEY (`occupation`(100)),
    KEY (`domicile`(100)),
    KEY (`age`(100)),
    KEY (`education`(100)),
    KEY (`text_id`),
    FOREIGN KEY (`text_id`) REFERENCES `text` (`id`) 
        ON DELETE CASCADE,
    FOREIGN KEY (`person_id`) REFERENCES `person` (`id`)
);

CREATE TABLE IF NOT EXISTS `variation` (
    `id`                BIGINT unsigned NOT NULL AUTO_INCREMENT,
    `text_id`           INT unsigned NOT NULL,
    `token_id`          INT unsigned NOT NULL,
    `operation`         TINYINT NOT NULL,
    `orig`              VARCHAR(80),
    `reg`               VARCHAR(80),
    `reg_bef`           VARCHAR(80),
    `reg_aft`           VARCHAR(80),
    `orig_bef`          VARCHAR(80),
    `orig_aft`          VARCHAR(80),
    `p_orig`            VARCHAR(80),
    `p_reg`             VARCHAR(80),
    `p_reg_bef`         VARCHAR(80),
    `p_reg_aft`         VARCHAR(80),
    `p_orig_bef`        VARCHAR(80),
    `p_orig_aft`        VARCHAR(80),
    --
    PRIMARY KEY (`id`),
    KEY (`operation`),
    KEY (`p_orig`),
    KEY (`p_reg`),
    KEY (`p_reg_aft`),
    KEY (`p_reg_bef`),
    KEY (`p_orig_aft`),
    KEY (`p_orig_bef`),
    KEY (`token_id`),
    KEY (`text_id`),
    FOREIGN KEY (`token_id`) REFERENCES `token` (`id`)
        ON DELETE CASCADE,
    FOREIGN KEY (`text_id`) REFERENCES `text` (`id`)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS `search` (
    `id`          INT unsigned NOT NULL AUTO_INCREMENT,
    `user_id`     INT unsigned NOT NULL,
    `query`       JSON NULL DEFAULT NULL,
    `name`        MEDIUMTEXT,
    `public`      TINYINT NOT NULL DEFAULT 0,
    `version`     VARCHAR(80),
    `created`     TIMESTAMP DEFAULT NOW(),
    --
    PRIMARY KEY (`id`),
    KEY (`public`),
    KEY (`user_id`),
    UNIQUE (`user_id`, `name`(80)),
    FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
);

CREATE TABLE IF NOT EXISTS `bibliography` (
    `id`           INT unsigned NOT NULL AUTO_INCREMENT,
    `data`         MEDIUMTEXT DEFAULT NULL,
    `updated`      TIMESTAMP DEFAULT NOW() ON UPDATE CURRENT_TIMESTAMP,
    --
    PRIMARY KEY (`id`)
);

CREATE TABLE IF NOT EXISTS `chapter` (
    `id`           INT unsigned NOT NULL AUTO_INCREMENT,
    `parent_id`    INT unsigned DEFAULT NULL,
    `title`        VARCHAR(512),
    `seq`          SMALLINT unsigned DEFAULT 1,
    `md`           MEDIUMTEXT DEFAULT NULL,
    `html`         MEDIUMTEXT DEFAULT NULL,
    `created`      TIMESTAMP DEFAULT NOW() ON UPDATE CURRENT_TIMESTAMP,
    --
    PRIMARY KEY (`id`),
    KEY (`seq`),
    FOREIGN KEY (`parent_id`) REFERENCES `chapter` (`id`)
);

INSERT INTO `chapter` (`parent_id`, `seq`, `title`, `md`, `html`) VALUES (NULL, '1', 'A Grammar of Documentary Greek', 'Welcome!', '<p>Welcome!</p>');
INSERT INTO `chapter` (`parent_id`, `seq`, `title`, `md`, `html`) VALUES (NULL, '2', 'Abbreviations', 'Text here', '<p>Text here</p>');
INSERT INTO `chapter` (`parent_id`, `seq`, `title`, `md`, `html`) VALUES (NULL, '3', 'Glossing and transliteration', 'Text here', '<p>Text here</p>');
INSERT INTO `chapter` (`parent_id`, `seq`, `title`, `md`, `html`) VALUES (NULL, '4', 'Bibliography', '', '');

CREATE TABLE IF NOT EXISTS `chapter_old_md` (
    `id`           INT unsigned NOT NULL AUTO_INCREMENT,
    `chapter_id`   INT unsigned NOT NULL,
    `user_id`      INT unsigned NOT NULL,
    `md`           MEDIUMTEXT DEFAULT NULL,
    `created`      TIMESTAMP DEFAULT NOW() ON UPDATE CURRENT_TIMESTAMP,
    --
    PRIMARY KEY (`id`),
    FOREIGN KEY (`chapter_id`) REFERENCES `chapter` (`id`)
        ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
);