"""Integration assertions run only on an explicitly selected disposable database."""
import os
import subprocess
import unittest


@unittest.skipUnless(os.environ.get('CONFIGSENTINEL_TEST_DB_CONTAINER'), 'isolated database container required')
class RuntimeDatabaseRoles(unittest.TestCase):
    def sql(self, statement, role='configsentinel_runtime'):
        return subprocess.run([
            'docker', 'exec', os.environ['CONFIGSENTINEL_TEST_DB_CONTAINER'],
            'psql', '-X', '-U', role, '-d', 'configsentinel', '-At',
            '-v', 'ON_ERROR_STOP=1', '-v', 'VERBOSITY=sqlstate', '-c', statement,
        ], capture_output=True, text=True)

    def test_runtime_allowed_and_denied_permissions(self):
        result = self.sql('SELECT current_user,rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname=current_user')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), 'configsentinel_runtime|f|f|f|f')
        self.assertEqual(self.sql('SELECT count(*) FROM users').returncode, 0)
        audit = "BEGIN; INSERT INTO audit_logs(id,organization_id,operation,target_type,target_id) SELECT gen_random_uuid(),id,'synthetic.review','organization',id FROM organizations LIMIT 1; ROLLBACK"
        self.assertEqual(self.sql(audit).returncode, 0)
        for sql in [
            'CREATE TABLE public.forbidden(id integer)',
            'CREATE SCHEMA forbidden',
            'ALTER TABLE users ADD COLUMN forbidden text',
            'UPDATE audit_logs SET operation=operation WHERE false',
            'DELETE FROM audit_logs WHERE false',
            'TRUNCATE audit_logs',
            'UPDATE schema_migrations SET version=version',
            'SET ROLE configsentinel_owner',
            'SET ROLE configsentinel_migrator',
            'ALTER ROLE configsentinel_runtime SUPERUSER',
        ]:
            with self.subTest(statement=sql):
                result = self.sql(sql)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('42501', result.stderr)

    def test_migrator_ownership_and_schema_rollback_compatibility(self):
        result = self.sql("BEGIN; SET ROLE configsentinel_owner; CREATE TABLE public.review_ddl(id integer); SELECT max(version) FROM schema_migrations; ROLLBACK", 'configsentinel_migrator')
        self.assertEqual(result.returncode, 0)
        self.assertIn('1', result.stdout.splitlines())
        result = self.sql("SET ROLE configsentinel_owner; SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tableowner<>'configsentinel_owner'", 'configsentinel_migrator')
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.stdout.strip().endswith('0'))
