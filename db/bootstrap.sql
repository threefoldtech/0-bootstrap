PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE provision (client varchar(32) primary key, branch varchar(256), zerotier varchar(32), kargs text);
COMMIT;
