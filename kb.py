import os
import sys
import logging
import json
import subprocess
import getpass
import datetime
import cloudant.client
import shortid
import editor
import yaml
import click
from python_json_config import ConfigBuilder

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "FATAL": logging.CRITICAL,
    "CRITICAL": logging.CRITICAL,
}
LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
LOG_FORMAT = "%(asctime)s %(name)s:%(levelname)s: %(message)s"

DEFAULT_CONFIG = {
    "couch_url":"http://localhost:5984",
    "database":"knowledge_base",
    "entitybase":"entities",
    "username":"",
    "password":""
}

def getLogger():
    return logging.getLogger('KB')

def loadConfiguration(config_path=None):
    if config_path is None:
        config_path = os.path.expanduser("~/.config/kb/kb.conf")
    builder = ConfigBuilder()
    builder.couch_url = DEFAULT_CONFIG['couch_url']
    builder.database = DEFAULT_CONFIG['database']
    builder.entitybase = DEFAULT_CONFIG['entitybase']
    builder.username = DEFAULT_CONFIG['username']
    builder.password = DEFAULT_CONFIG['password']
    config = builder.parse_config(config_path)
    return config


class KBManager(object):

    def __init__(self, config):
        self._L = getLogger()
        self.config = config
        self._shortid = shortid.ShortId()
        self.client = None
        self._connect()

    def _connect(self):
        self._L.debug(str(self.config))
        if self.client is None:
            self.client = cloudant.client.CouchDB(
                self.config.username,
                self.config.password,
                url=self.config.couch_url
            )
            self.client.connect()

    def __del__(self):
        self._L.debug("KBManager.__del__")
        try:
            self.client.disconnect()
        except Exception as e:
            self._L.debug("Exception on __del__: %s", e)

    def getKB(self):
        db = None
        try:
            db = self.client[self.config.database]
        except KeyError as e:
            self._L.info("Knowledgebase doesn't exist. Creating...")
            db = self.client.create_database(self.config.database)
        return db


    def createRecord(self, record):
        db = self.getKB()
        return db.create_document(record)


    def listTags(self):
        db = self.getKB()
        options = {"group":True}
        for row in db.get_view_result("uniqueTags", 'tags', **options):
            #print(row.get('key',''))
            print(row)


    def listRecords(self, match_context=None, match_tags=None, match_text=None):
        db = self.getKB()
        if match_context is None and match_tags is None and match_text is None:
            for doc in db:
                if isinstance(doc, cloudant.design_document.DesignDocument):
                    continue
                print(f"{doc['_id']} {doc['context']} {' | '.join(doc['tags'])}")


    def deleteRecord(self, rid):
        db = self.getKB()
        try:
            doc = db[rid]
        except Exception as e:
            self._L.error(e)
            return
        if not doc is None:
            doc.delete()


    def editRecord(self, rid):
        db = self.getKB()
        try:
            doc = db[rid]
        except Exception as e:
            self._L.error(e)
            return
        meta = doc.copy()
        meta.pop("message")
        document = "---\n"
        document += yaml.dump(meta)
        document += "---\n"
        document += doc["message"]
        content = editor.edit(contents=document).decode().split("\n")
        meta_part = ""
        document = ""
        meta_start = -1
        meta_end = 0
        line_no = 0
        for line in content:
            if line.strip() == "---":
                if meta_start < 0:
                    meta_start = line_no
                else:
                    meta_end = line_no
                    break
            line_no += 1
        meta_part = "\n".join(content[meta_start+1 : meta_end-1])
        document = "\n".join(content[meta_end+1:])
        meta = yaml.load(meta_part, Loader=yaml.Loader)
        for k,v in meta.items():
            doc[k] = v
        doc["message"] = document
        print(str(meta))
        print(doc["message"])
        doc.save()


    def generateIdentifier(self, prefix="kb"):
        res = f"{prefix}:{self._shortid.generate()}"
        return res

@click.group(invoke_without_command=True)
@click.option(
    "-v",
    "--verbosity",
    default="INFO",
    help="Specify logging level",
    show_default=True,
)
@click.option(
    "-c",
    "--context",
    default=os.path.abspath("."),
    help="Context of entry"
)
@click.pass_context
def main(ctx, verbosity, context):
    ctx.ensure_object(dict)
    verbosity = verbosity.upper()
    logging.basicConfig(
        level=LOG_LEVELS.get(verbosity, logging.INFO),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )
    L = getLogger()
    if verbosity not in LOG_LEVELS.keys():
        L.warning("%s is not a log level, set to INFO", verbosity)
    config = loadConfiguration()
    ctx.obj['kb'] = KBManager(config)
    ctx.obj['L'] = L
    ctx.obj['context'] = context
    if ctx.invoked_subcommand is None:
        ctx.invoke(list_tags)
    return


@main.command(name='tags')
@click.pass_context
def list_tags(ctx):
    kb = ctx.obj.get('kb')
    kb.listTags()

@main.command(name='list')
@click.pass_context
def list_entries(ctx):
    kb = ctx.obj.get('kb')
    kb.listRecords()

@main.command(name='edit')
@click.pass_context
@click.argument("identifier", default=None)
def edit_entry(ctx, identifier):
    kb = ctx.obj.get('kb')
    if identifier is None:
        ctx.obj['L'].error("Entry identifier is required.")
        return 1
    kb.editRecord(identifier.strip())
    return 0

@main.command(name='delete')
@click.pass_context
@click.argument("identifier", default=None)
def edit_entry(ctx, identifier):
    kb = ctx.obj.get('kb')
    if identifier is None:
        ctx.obj['L'].error("Entry identifier is required.")
        return 1
    kb.deleteRecord(identifier.strip())
    return 0

@main.command(name='create')
@click.pass_context
@click.option('-t','--tags', help='Tag for entry (multiple allowed)', multiple=True, default=['general'])
@click.argument('message', default='')
def create_entry(ctx, tags, message):
    kb = ctx.obj.get('kb')
    L = ctx.obj['L']
    res = {
        "_id": kb.generateIdentifier(),
        "hostname":subprocess.check_output(['hostname','-f']).decode().strip(),
        "user": getpass.getuser(),
        "created": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "context": ctx.obj['context'],
        "tags": tags,
        "message": message,
    }
    logging.debug(json.dumps(res, indent=2))
    res = kb.createRecord(res)
    kb.editRecord(res["_id"])
    return 0

if __name__ == "__main__":
    sys.exit(main())
