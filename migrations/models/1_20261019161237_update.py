from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "accounts" (
    "id" CHAR(36) NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMP NOT NULL,
    "updated_at" TIMESTAMP,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "password" VARCHAR(255) NOT NULL,
    "last_login" TIMESTAMP,
    "is_active" INT NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_accounts_id_f8ee81" ON "accounts" ("id", "name", "email");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "accounts";"""


MODELS_STATE = (
    "eJztWG1P2zAQ/itRPnUSQ1DKi6ZpUgud6ERbBGGbQMhyEze1cOyQOEDF+t/nc5LmpW1EEB"
    "0w8aVtnruLz89j+3x9ND3hEBZutm1bRFyaX4xHk2OPqB9l04ZhYt/PDABIPGLaF8dOGsSj"
    "UAbYhpeNMQuJghwS2gH1JRVcoTxiDEBhK0fK3QyKOL2NCJLCJXJCAmW4ulYw5Q55ICE8Xp"
    "nUgUF0kuqbeJgy8xq8/Bs0poQ5hUnE3hpHcupr7OKid/Rde0IWI2QLFnk88/anciL43D2K"
    "qLMJMWBzCScBlsTJzQ6ST4hIoXgiCpBBROYzcDLAIWMcMeDI/DqOuA3UGHok+Gh9S1LLuS"
    "E0GFrovGshZNag1BYc5KAgjiJmFr83I0SjJgxweNw+a+zsfdIUiFC6gTZqusyZDsQSx6Fa"
    "i4xlOyDACcJyke0jZZHUI8sZL0aWmHeS0M30x3MUSIFMgmxVpuSm9K2BcFNN0BlyNk20rx"
    "DA6vW751a7fwrDeWF4yzR/basLlqZGpyW0Eesl1IaLd+L8JcavnnVswKNxORx0y6rO/axL"
    "E3LCkRSIi3uEndwyTdGUNeWZqR75zjNVL0a+gOpJum9F9HcicspJpcrpSVvU93CCg+Xapv"
    "4lVRU96zk/17l3PfyAGOGunKjH5u5uha4/22f6AFVeJbEGiakZ22YFduP6VYPeecAHv0/h"
    "18dheC+CJbeA1RTnY16G5deuQevnmeFQIiZcyuvWgmLkRy14y7WAhkhd7OndkoLQEYIRzF"
    "fcq/NxJYlHKnBde2qO/FtdO8PhSUHSTs8q7aWLfqd71tjWWionKjXcG1hqX0EzM77JXbQB"
    "GGH75h4HDlqwiKZY5bto8ppeGcEcu5o/mCfMKm38SEDtibmsJYwtG5UdYeazzn6wVuPX47"
    "JG30fjpje/LpOj5e0WVBdS+Nzcbu23Dnb2WgfKRac5R/Yrlm28+jYq+rw7EoSQUo1imgv5"
    "qKVPq6WwqWownLj/h+xub209gV3ltZJdbSuyq0aUhC9pWX+cDwcr/qTIQsr3E2pL44/BaL"
    "hwVrwDtivIBTIKJSzltNFv/y7TfXgy7JSvG/CCzmsXs9lfIfOktA=="
)
