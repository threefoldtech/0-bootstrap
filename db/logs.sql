PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE logs (client varchar(64), hit text, timestamp datetime);
CREATE INDEX logs_client on logs (client);
COMMIT;
