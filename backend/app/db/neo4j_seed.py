"""
Seed Neo4j with a sample microservices infrastructure graph.
Run: uv run python -m app.db.neo4j_seed
"""
import asyncio

from app.db.neo4j import neo4j_driver
from logger import logger


SEED_STATEMENTS = [
    "MATCH (n) DETACH DELETE n",
    "CREATE (:Service {name:'api-gateway',type:'Service',status:'healthy',region:'us-east-1'})",
    "CREATE (:Service {name:'checkout-service',type:'Service',status:'degraded',region:'us-east-1'})",
    "CREATE (:Service {name:'payment-service',type:'Service',status:'healthy',region:'us-east-1'})",
    "CREATE (:Service {name:'inventory-service',type:'Service',status:'healthy',region:'us-east-1'})",
    "CREATE (:Service {name:'notification-service',type:'Service',status:'healthy',region:'us-east-1'})",
    "CREATE (:Service {name:'user-service',type:'Service',status:'healthy',region:'us-east-1'})",
    "CREATE (:Service {name:'mobile-bff',type:'Service',status:'healthy',region:'us-east-1'})",
    "CREATE (:Database {name:'postgres-primary',type:'Database',status:'healthy',engine:'PostgreSQL'})",
    "CREATE (:Database {name:'postgres-replica',type:'Database',status:'healthy',engine:'PostgreSQL'})",
    "CREATE (:Cache {name:'redis-cache',type:'Cache',status:'healthy',engine:'Redis'})",
    "CREATE (:Queue {name:'kafka-events',type:'Queue',status:'healthy',engine:'Kafka'})",
    "CREATE (:Team {name:'platform-team',slack:'#platform-alerts'})",
    "CREATE (:Team {name:'payments-team',slack:'#payments-on-call'})",
    "CREATE (:Team {name:'checkout-team',slack:'#checkout-squad'})",
    "CREATE (:Deployment {id:'deploy-001',version:'v2.3.1',service:'checkout-service',status:'completed',timestamp:'2024-01-15T10:30:00Z',author:'ci-bot'})",
    "CREATE (:Deployment {id:'deploy-002',version:'v1.9.0',service:'payment-service',status:'completed',timestamp:'2024-01-14T08:00:00Z',author:'ci-bot'})",
    "CREATE (:Incident {id:'INC-001',severity:'P1',description:'Checkout latency spike post-deploy',status:'resolved',timestamp:'2024-01-15T11:00:00Z'})",
    "CREATE (:Incident {id:'INC-002',severity:'P2',description:'Redis connection pool exhaustion',status:'resolved',timestamp:'2024-01-10T14:00:00Z'})",
    "CREATE (:Runbook {id:'RB-001',title:'Checkout Service Rollback',url:'https://wiki.internal/runbooks/checkout-rollback'})",
    "CREATE (:Runbook {id:'RB-002',title:'Redis Cache Flush',url:'https://wiki.internal/runbooks/redis-flush'})",
    "CREATE (:Runbook {id:'RB-003',title:'Payment Service Escalation',url:'https://wiki.internal/runbooks/payment-escalation'})",
    """MATCH (a:Service {name:'api-gateway'}),(c:Service {name:'checkout-service'}) CREATE (a)-[:DEPENDS_ON]->(c)""",
    """MATCH (a:Service {name:'api-gateway'}),(u:Service {name:'user-service'}) CREATE (a)-[:DEPENDS_ON]->(u)""",
    """MATCH (m:Service {name:'mobile-bff'}),(a:Service {name:'api-gateway'}) CREATE (m)-[:DEPENDS_ON]->(a)""",
    """MATCH (c:Service {name:'checkout-service'}),(p:Service {name:'payment-service'}) CREATE (c)-[:DEPENDS_ON]->(p)""",
    """MATCH (c:Service {name:'checkout-service'}),(i:Service {name:'inventory-service'}) CREATE (c)-[:DEPENDS_ON]->(i)""",
    """MATCH (c:Service {name:'checkout-service'}),(db:Database {name:'postgres-primary'}) CREATE (c)-[:DEPENDS_ON]->(db)""",
    """MATCH (c:Service {name:'checkout-service'}),(r:Cache {name:'redis-cache'}) CREATE (c)-[:DEPENDS_ON]->(r)""",
    """MATCH (p:Service {name:'payment-service'}),(db:Database {name:'postgres-primary'}) CREATE (p)-[:DEPENDS_ON]->(db)""",
    """MATCH (p:Service {name:'payment-service'}),(k:Queue {name:'kafka-events'}) CREATE (p)-[:DEPENDS_ON]->(k)""",
    """MATCH (i:Service {name:'inventory-service'}),(db:Database {name:'postgres-replica'}) CREATE (i)-[:DEPENDS_ON]->(db)""",
    """MATCH (n:Service {name:'notification-service'}),(k:Queue {name:'kafka-events'}) CREATE (n)-[:DEPENDS_ON]->(k)""",
    """MATCH (u:Service {name:'user-service'}),(db:Database {name:'postgres-primary'}) CREATE (u)-[:DEPENDS_ON]->(db)""",
    """MATCH (c:Service {name:'checkout-service'}),(t:Team {name:'checkout-team'}) CREATE (c)-[:OWNED_BY]->(t)""",
    """MATCH (p:Service {name:'payment-service'}),(t:Team {name:'payments-team'}) CREATE (p)-[:OWNED_BY]->(t)""",
    """MATCH (a:Service {name:'api-gateway'}),(t:Team {name:'platform-team'}) CREATE (a)-[:OWNED_BY]->(t)""",
    """MATCH (d:Deployment {id:'deploy-001'}),(c:Service {name:'checkout-service'}) CREATE (d)-[:DEPLOYED_IN]->(c)""",
    """MATCH (d:Deployment {id:'deploy-002'}),(p:Service {name:'payment-service'}) CREATE (d)-[:DEPLOYED_IN]->(p)""",
    """MATCH (i:Incident {id:'INC-001'}),(c:Service {name:'checkout-service'}) CREATE (i)-[:AFFECTS]->(c)""",
    """MATCH (i:Incident {id:'INC-001'}),(a:Service {name:'api-gateway'}) CREATE (i)-[:AFFECTS]->(a)""",
    """MATCH (i:Incident {id:'INC-001'}),(d:Deployment {id:'deploy-001'}) CREATE (i)-[:TRIGGERED_BY]->(d)""",
    """MATCH (i:Incident {id:'INC-002'}),(r:Cache {name:'redis-cache'}) CREATE (i)-[:AFFECTS]->(r)""",
    """MATCH (c:Service {name:'checkout-service'}),(r:Runbook {id:'RB-001'}) CREATE (c)-[:HAS_RUNBOOK]->(r)""",
    """MATCH (r:Cache {name:'redis-cache'}),(rb:Runbook {id:'RB-002'}) CREATE (r)-[:HAS_RUNBOOK]->(rb)""",
    """MATCH (p:Service {name:'payment-service'}),(r:Runbook {id:'RB-003'}) CREATE (p)-[:HAS_RUNBOOK]->(r)""",
]


async def seed() -> None:
    logger.info("Seeding Neo4j...")
    async with neo4j_driver.session() as session:
        for stmt in SEED_STATEMENTS:
            await session.run(stmt.strip())
    logger.info("Neo4j seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())