"""
Couchdb Manager

https://python-cloudant.readthedocs.io/en/stable/
"""
import sys
from cloudant import couchdb
import cloudant.security_document
import click
from pprint import pprint
import logging

import passify

logging.getLogger(__name__).addHandler(logging.NullHandler())


ADMIN_KEY = "couchdb.slap.admin"


class CouchManager(object):

    def __init__(self, password, user='admin', url='http://localhost:5984'):
        self._user = user
        self._pass = password
        self._url = url
        self._user_db = "_users"
        self._metadata = {}
        with couchdb(self._user, self._pass, url=self._url) as client:
            self._metadata = client.metadata()


    def listDatabases(self):
        with couchdb(self._user, self._pass, url=self._url) as client:
            print(f"Documents Database")
            print(f"========= =====================")
            for db in client.all_dbs():
                print(f"{client[db].doc_count():9} {db}")
            print(f"========= =====================")


    def compactDatabase(self, dbname):
        """
        https://docs.couchdb.org/en/stable/maintenance/compaction.html

        Args:
            dbname:

        Returns:

        """
        with couchdb(self._user, self._pass, url=self._url) as client:
            url = "/".join((self._url, dbname, "_compact"))
            logging.debug("Compacting %s", dbname)
            response = client.r_session.post(url, headers={'Content-Type': 'application/json'})
            logging.debug(response)
            logging.debug(response.text)


    def listUsers(self):
        """
        List all users known to CouchDB instance.

        Returns:

        """
        with couchdb(self._user, self._pass, url=self._url) as client:
            db = client["_users"]
            alldocs = db.all_docs(include_docs=True)
            for doc in alldocs['rows']:
                if doc['doc']['_id'].startswith("org.couchdb.user"):
                    print(f"{doc['doc']['_id']}")
                    print(f"  username: {doc['doc']['name']}")
                    print(f"  roles: {','.join(doc['doc']['roles'])}")


    def addUser(self, username, password, roles:[]):
        """
        Adds a user to the CouchDB instance. A user can then be added to a database.
        Args:
            username:
            password:
            roles:

        Returns:

        """
        credentials = {
            "_id":f"org.couchdb.user:{username}",
            "name":username,
            "type":"user",
            "roles": roles,
            "password": password
        }
        with couchdb(self._user, self._pass, url=self._url) as client:
            user_db = client["_users"]
            user_db.create_document(credentials, throw_on_exists=True)


    def createDatabase(self, dbname):
        pass

    def deleteDatabase(self, dbname):
        pass


    def getDatabaseRoles(self, dname):
        pass

    def addDatabaseRole(self, dbname, role):
        pass


    def addDatabaseUser(self, dbname, username, roles=[]):
        pass

    def getDatabaseUsers(self, dbname):
        with couchdb(self._user, self._pass, url=self._url) as client:
            db = client[dbname]
            print(f"Admin party:\n{db.admin_party}")
            creds = db.creds
            print("Database credentials document:")
            pprint(creds)
            print("Security documents:")
            counter = 0
            with cloudant.security_document.SecurityDocument(db) as secdoc:
                print(f"[{counter}] {secdoc.json()}")
                counter += 1


    def getDatabaseDesigns(self, dbname):
        with couchdb(self._user, self._pass, url=self._url) as client:
            db = client[dbname]
            docs = db.design_documents()
            for item in docs:
                doc = item['doc']
                for k,v in doc.items():
                    print(f"{k}\n  {v}")



@click.command()
@click.argument('operation', default="list")
@click.option('-l','--loglevel', default=0, count=True, help="Logging verbosity")
@click.option('-d', '--database', default=None, help="Database name")
@click.option('-k','--admin_key', default=ADMIN_KEY, help="Bitwarden entry key for CouchDB credentials")
@click.option('--username', default=None, help="Username for adding or modifying a user")
@click.option('--password', default=None, help="User password to use when adding or modifying a user")
@click.option('--roles', default="", help="Comma delimited list of roles for the user")
def main(operation, database=None, admin_key=ADMIN_KEY, loglevel=0, username=None, password=None, roles=""):
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(len(levels) - 1, loglevel)]
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")

    operation = operation.lower()
    creds = passify.getCredentials(key=admin_key)
    CM = CouchManager(creds['password'], creds['username'], creds["url"])
    if operation == 'list':
        CM.listDatabases()
        return 0
    if operation == 'users':
        if database is None:
            CM.listUsers()
            return 0
        CM.getDatabaseUsers(database)
        return 0
    if operation == 'designs':
        if database is None:
            logging.error("Database name is required when listing design documents.")
            return 1
        CM.getDatabaseDesigns(database)
        return 0
    if operation == 'compact':
        if database is None:
            logging.error("Database name is reqired for initiating compaction.")
            return 1
        CM.compactDatabase(database)
        return 0
    if operation == "adduser":
        if username is None:
            logging.error("Username is required when adding a user.")
            return 1
        if password is None:
            logging.error("Password is required when adding a user.")
            return 1
        role_list = []
        roles = roles.strip()
        if len(roles) > 0:
            role_list = roles.split(",")
        CM.addUser(username, password, roles=role_list)
    return 0


if __name__ == "__main__":
    sys.exit(main())