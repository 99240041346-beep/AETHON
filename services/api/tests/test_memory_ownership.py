from aethon.memory_engine import PersistentMemoryEngine
from aethon.memory_repository import MemoryRepository


def test_local_memory_owner_isolation():
    memory = PersistentMemoryEngine()
    memory.put('same-project-a', 'secret project context', owner_id='alice', project_id='p', namespace='project')
    memory.put('same-project-b', 'other project context', owner_id='bob', project_id='p', namespace='project')
    assert [r.memory_id for r in memory.search('context', owner_id='alice', project_id='p', namespace='project')] == ['same-project-a']
    assert [r.memory_id for r in memory.search('context', owner_id='bob', project_id='p', namespace='project')] == ['same-project-b']


def test_repository_uses_postgres_when_configured():
    repository = MemoryRepository(database_url='postgresql://example.invalid/aethon')
    assert repository.use_postgres is True
