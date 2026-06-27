import asyncio
import aiomysql
import os

os.environ.setdefault("DATABASE_URL", "mysql+aiomysql://root@localhost:3308/care_assist")


async def main():
    conn = await aiomysql.connect(host="localhost", port=3308, user="root", db="care_assist")
    async with conn.cursor() as cur:
        await cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        await cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'care_assist'"
        )
        tables = [row[0] for row in await cur.fetchall()]
        for table in tables:
            print(f"Dropping {table}")
            await cur.execute(f"DROP TABLE IF EXISTS `{table}`")
        await cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    await conn.commit()
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
    print("All tables dropped")
