"""种子数据脚本：往数据库灌入第一批运维知识文档。

运行方式：python -m app.seed_data
"""

from sqlalchemy import func, select

from .database import SessionLocal
from .init_db import create_database, create_tables
from .models import Category, KnowledgeDoc

# ---------- 第一部分：种子数据（初始写死的"书"） ----------

SEED_CATEGORIES = [
    {"name": "mysql", "description": "MySQL 数据库运维知识"},
    {"name": "redis", "description": "Redis 缓存运维知识"},
    {"name": "linux", "description": "Linux 服务器运维基础"},
]

SEED_DOCS = [
    # ================= MySQL =================
    {
        "category": "mysql",
        "title": "MySQL 主从复制原理",
        "content": (
            "主库开启 binlog 记录所有写操作，从库通过 I/O 线程把主库的 binlog "
            "拉取到本地的 relay log，再由 SQL 线程重放，实现数据同步。"
            "复制默认是异步的，因此存在主从延迟。生产环境 binlog 格式推荐 ROW。"
        ),
        "tags": "主从复制,binlog,高可用",
        "source": "运维实战总结",
    },
    {
        "category": "mysql",
        "title": "如何定位慢查询",
        "content": (
            "开启慢查询日志 slow_query_log，设置 long_query_time 阈值（如 1 秒）。"
            "用 mysqldumpslow 工具或直接查 mysql.slow_log 表分析慢 SQL。"
            "对慢 SQL 执行 EXPLAIN 查看执行计划，重点关注 type、key、rows 三个字段。"
        ),
        "tags": "慢查询,优化,EXPLAIN",
        "source": "运维实战总结",
    },
    {
        "category": "mysql",
        "title": "索引失效的常见场景",
        "content": (
            "对索引列使用函数或计算、左模糊 LIKE '%xx'、隐式类型转换、"
            "OR 连接非索引列、不满足联合索引最左前缀原则等，都会导致索引失效，"
            "退化为全表扫描。排查时用 EXPLAIN 看是否走了索引。"
        ),
        "tags": "索引,优化",
        "source": "运维实战总结",
    },
    {
        "category": "mysql",
        "title": "MySQL 事务隔离级别",
        "content": (
            "四种隔离级别：READ UNCOMMITTED 可能脏读；READ COMMITTED 可能不可重复读；"
            "REPEATABLE READ 是 InnoDB 默认级别，通过 MVCC 加间隙锁解决幻读；"
            "SERIALIZABLE 完全串行但并发最差。隔离级别越高，并发能力越低。"
        ),
        "tags": "事务,隔离级别,MVCC",
        "source": "运维实战总结",
    },
    {
        "category": "mysql",
        "title": "MVCC 原理简述",
        "content": (
            "InnoDB 通过 undo log 保存行的历史版本，每行隐藏 trx_id 字段。"
            "普通查询通过 ReadView 判断哪个版本对当前事务可见，"
            "从而在不加锁的情况下实现一致性读，大大提升并发能力。"
        ),
        "tags": "MVCC,undo log,一致性读",
        "source": "运维实战总结",
    },
    {
        "category": "mysql",
        "title": "InnoDB 与 MyISAM 的区别",
        "content": (
            "InnoDB 支持事务、行级锁、外键和崩溃恢复，数据按主键聚簇存放，是默认引擎。"
            "MyISAM 只支持表级锁、不支持事务，适合只读场景，但已逐步被淘汰。"
            "线上业务表应使用 InnoDB。"
        ),
        "tags": "存储引擎,InnoDB,MyISAM",
        "source": "运维实战总结",
    },
    {
        "category": "mysql",
        "title": "主从延迟的原因与解决",
        "content": (
            "常见原因：大事务、DDL、从库单线程重放、硬件差异。"
            "解决思路：拆分大事务、开启并行复制（slave_parallel_workers）、"
            "考虑半同步复制保证可靠性，以及读写分离时把实时性要求高的读打到主库。"
        ),
        "tags": "主从延迟,并行复制,半同步",
        "source": "运维实战总结",
    },
    {
        "category": "mysql",
        "title": "binlog 的三种格式",
        "content": (
            "STATEMENT 记录原始 SQL，日志量小但结果可能不一致；"
            "ROW 记录每行数据的变更，最安全但日志量大；"
            "MIXED 由 MySQL 自动选择。生产环境推荐使用 ROW 格式。"
        ),
        "tags": "binlog,复制",
        "source": "运维实战总结",
    },
    {
        "category": "mysql",
        "title": "大表加索引与在线 DDL",
        "content": (
            "直接 ALTER TABLE 加索引可能长时间锁表，影响线上业务。"
            "可优先用 MySQL 8 的 INSTANT/INPLACE 算法，或使用 gh-ost、pt-osc "
            "等在线变更工具，先在从库演练，再切换主库。"
        ),
        "tags": "DDL,在线变更,gh-ost",
        "source": "运维实战总结",
    },
    {
        "category": "mysql",
        "title": "连接数被打满怎么办",
        "content": (
            "先用 SHOW PROCESSLIST 查看会话状态和来源，定位是慢查询堆积还是连接泄漏。"
            "调大 max_connections 只是缓解，根因通常是慢 SQL 或连接池配置不当；"
            "可临时 kill 空闲连接，并从应用层检查连接池大小和超时设置。"
        ),
        "tags": "连接数,processlist,排查",
        "source": "运维实战总结",
    },
    # ================= Redis =================
    {
        "category": "redis",
        "title": "Redis 持久化 RDB 与 AOF",
        "content": (
            "RDB 是定时生成全量快照，恢复快，但可能丢失最后一次快照之后的数据；"
            "AOF 记录每一条写命令，数据丢失少但文件大、恢复慢。"
            "重启恢复时 AOF 优先于 RDB。生产环境建议两者同时开启。"
        ),
        "tags": "持久化,RDB,AOF",
        "source": "运维实战总结",
    },
    {
        "category": "redis",
        "title": "Redis 过期删除策略",
        "content": (
            "Redis 使用惰性删除加定期删除结合：访问 key 时发现过期才删除，"
            "同时后台定期随机抽查一批带过期时间的 key 进行删除。"
            "因此过期 key 不会立刻消失，仍可能占用内存。"
        ),
        "tags": "过期策略,内存",
        "source": "运维实战总结",
    },
    {
        "category": "redis",
        "title": "Redis 内存淘汰策略",
        "content": (
            "noeviction 内存满后直接报错；allkeys-lru 在全部 key 中淘汰最近最少使用；"
            "volatile-lru 只在设置了过期时间的 key 中淘汰。"
            "其他还有 lfu、random、ttl 等，通过 maxmemory-policy 配置。"
        ),
        "tags": "内存淘汰,LRU,LFU",
        "source": "运维实战总结",
    },
    {
        "category": "redis",
        "title": "缓存穿透、击穿与雪崩",
        "content": (
            "穿透：查询根本不存在的 key，每次都打到数据库，用布隆过滤器或缓存空值解决。"
            "击穿：某个热点 key 过期的瞬间大量请求打到数据库，用互斥锁或逻辑过期解决。"
            "雪崩：大量 key 同时过期，用随机过期时间和多级缓存分散压力。"
        ),
        "tags": "缓存穿透,缓存击穿,缓存雪崩",
        "source": "运维实战总结",
    },
    {
        "category": "redis",
        "title": "Redis 哨兵（Sentinel）原理",
        "content": (
            "哨兵负责监控主从节点、自动通知和故障转移。"
            "当主库疑似下线，多个哨兵投票确认客观下线后，从从库中选举新主库。"
            "生产环境至少部署 3 个哨兵实例形成奇数，避免脑裂。"
        ),
        "tags": "哨兵,Sentinel,高可用",
        "source": "运维实战总结",
    },
    {
        "category": "redis",
        "title": "Redis Cluster 集群",
        "content": (
            "集群将 key 按 CRC16 哈希对 16384 个槽取模后分布到不同节点。"
            "节点间通过 gossip 协议互相通信，每个主节点可挂从节点。"
            "客户端访问时需处理 MOVED 和 ASK 重定向。"
        ),
        "tags": "集群,槽位,高可用",
        "source": "运维实战总结",
    },
    {
        "category": "redis",
        "title": "缓存与数据库一致性",
        "content": (
            "常用 Cache Aside 模式：读时先查缓存，未命中再查数据库并回填；"
            "写时先更新数据库，再删除缓存。极端场景可用延迟双删"
            "（删缓存、等待短暂时间、再删一次）。应避免先删缓存再写数据库。"
        ),
        "tags": "一致性,Cache Aside,延迟双删",
        "source": "运维实战总结",
    },
    {
        "category": "redis",
        "title": "大 key 与热 key 问题",
        "content": (
            "大 key（如超大 hash、list）会阻塞单线程命令执行并造成内存分布不均，"
            "需要拆分或使用更细粒度的数据结构。热 key 单个节点压力过大，"
            "可通过本地缓存、读写分离、把热 key 打散到多个副本等方式缓解。"
        ),
        "tags": "大key,热key,性能",
        "source": "运维实战总结",
    },
    {
        "category": "redis",
        "title": "Redis 单线程为什么快",
        "content": (
            "基于内存、数据结构高效、使用 IO 多路复用（epoll）管理大量连接，"
            "同时避免了多线程的上下文切换和锁竞争。"
            "代价是单个命令必须执行得快，因此要避免大 key 和慢命令。"
        ),
        "tags": "单线程,IO多路复用,性能",
        "source": "运维实战总结",
    },
    {
        "category": "redis",
        "title": "Redis 分布式锁",
        "content": (
            "用 SET key value NX EX 秒 实现加锁，value 存唯一标识防止误删别人的锁；"
            "释放时用 Lua 脚本先比对 value 再删除，保证原子性。"
            "高可用场景可使用 Redlock 算法，但工程上多数场景单主实例足够。"
        ),
        "tags": "分布式锁,原子性,Lua",
        "source": "运维实战总结",
    },
    # ================= Linux =================
    {
        "category": "linux",
        "title": "系统负载怎么看",
        "content": (
            "uptime 输出 load average 三个值，分别代表 1、5、15 分钟的平均负载。"
            "负载接近 CPU 核数说明系统繁忙，明显超过核数说明排队严重。"
            "top 命令可以按 CPU 或内存排序查看具体进程。"
        ),
        "tags": "负载,uptime,top",
        "source": "运维实战总结",
    },
    {
        "category": "linux",
        "title": "排查 CPU 占用高",
        "content": (
            "先用 top 按 P 排序找到 CPU 高的进程，再用 pidstat -p PID 1 观察线程，"
            "最后可用 perf top 定位热点函数。常见原因：死循环、频繁 GC、"
            "或数据库慢查询在应用侧聚合计算。"
        ),
        "tags": "CPU,排查,pidstat",
        "source": "运维实战总结",
    },
    {
        "category": "linux",
        "title": "磁盘满了怎么办",
        "content": (
            "用 df -h 查看各挂载点使用率，用 du -sh /* 逐层定位大目录。"
            "找到大文件后确认能否删除、归档或压缩。"
            "还要用 lsof | grep deleted 查找已被删除但仍被进程占用、"
            "导致空间不释放的文件。"
        ),
        "tags": "磁盘,df,du,lsof",
        "source": "运维实战总结",
    },
    {
        "category": "linux",
        "title": "查看端口占用",
        "content": (
            "ss -lntp 可查看监听端口和对应进程，lsof -i:端口号 也能定位占用者。"
            "排查服务连不上时，依次确认端口是否有监听、进程是否存活、"
            "防火墙是否放行。"
        ),
        "tags": "端口,ss,lsof",
        "source": "运维实战总结",
    },
    {
        "category": "linux",
        "title": "systemd 管理服务",
        "content": (
            "systemctl start/stop/restart/status/enable 可管理服务，"
            "enable 表示开机自启。查看服务日志用 journalctl -u 服务名 -f。"
            "自定义服务需要编写 /etc/systemd/system/ 下的 .service 文件。"
        ),
        "tags": "systemd,systemctl,journalctl",
        "source": "运维实战总结",
    },
    {
        "category": "linux",
        "title": "日志查看技巧",
        "content": (
            "tail -f 实时跟踪日志，grep 过滤关键字，awk/sed 可做进一步处理。"
            "systemd 服务日志用 journalctl -u 服务名 --since '1 hour ago' 按时间查询。"
            "日志量大时先 grep 缩小范围，再针对性分析。"
        ),
        "tags": "日志,tail,grep,journalctl",
        "source": "运维实战总结",
    },
    {
        "category": "linux",
        "title": "Linux 文件权限",
        "content": (
            "rwx 分别代表读 4、写 2、执行 1。chmod 755 表示属主可读写执行，"
            "组和其他用户只读执行。chown 修改文件属主。"
            "遇到权限不足先 ls -l 查看属主、属组和当前权限。"
        ),
        "tags": "权限,chmod,chown",
        "source": "运维实战总结",
    },
]


# ---------- 第二部分：写入逻辑 ----------


def seed() -> None:
    """主流程：建库建表 → 插分类 → 插文档 → 查询验证。"""
    # 确保数据库和表存在（脚本可反复执行，不会重复建）
    create_database()
    create_tables()

    db = SessionLocal()
    try:
        # 1) 插入分类，name 存在则跳过（防止重复）
        category_map = {}
        for cat in SEED_CATEGORIES:
            exists = db.scalar(select(Category).where(Category.name == cat["name"]))
            if exists:
                print(f"⏭️  分类 {cat['name']} 已存在，跳过")
                category_map[cat["name"]] = exists
            else:
                new_cat = Category(**cat)
                db.add(new_cat)
                db.flush()  # flush 先拿到自增 id，但还没真正提交
                category_map[cat["name"]] = new_cat
                print(f"➕ 新增分类 {cat['name']}")

        db.commit()  # 提交分类

        # 2) 插入知识文档，标题已存在则跳过
        added = 0
        for doc in SEED_DOCS:
            exists = db.scalar(
                select(KnowledgeDoc).where(KnowledgeDoc.title == doc["title"])
            )
            if exists:
                print(f"⏭️  文档《{doc['title']}》已存在，跳过")
                continue
            db.add(
                KnowledgeDoc(
                    title=doc["title"],
                    content=doc["content"],
                    tags=doc["tags"],
                    source=doc["source"],
                    category_id=category_map[doc["category"]].id,
                )
            )
            added += 1

        db.commit()
        print(f"✅ 本次新增 {added} 篇文档")

        # 3) 验证：统计每个分类有多少篇文档
        print("\n--- 数据验证 ---")
        rows = db.execute(
            select(Category.name, func.count(KnowledgeDoc.id))
            .join(KnowledgeDoc, KnowledgeDoc.category_id == Category.id)
            .group_by(Category.name)
        ).all()
        for name, count in rows:
            print(f"分类 {name}: {count} 篇")

        total = db.scalar(select(func.count(KnowledgeDoc.id)))
        print(f"知识文档总数: {total} 篇")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
