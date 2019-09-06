import io
import json
import cx_Oracle
import oci
import os
import shutil
import logging
from zipfile import ZipFile

from fdk import response

#OCI_CONFIG_LOC = "/function/.oci/config"

def get_dbwallet(bucket_name, object_name):
    # authentication based on instance principal
    signer = oci.auth.signers.get_resource_principals_signer()
    object_storage_client = oci.object_storage.ObjectStorageClient(config={}, signer=signer)
    # authentication based on oci config
    #config = oci.config.from_file(file_location=OCI_CONFIG_LOC)
    #object_storage_client = oci.object_storage.ObjectStorageClient(config)
    # common
    obj = object_storage_client.get_object(
        object_storage_client.get_namespace().data, bucket_name, object_name)
    dbwallet_dir = os.environ['TNS_ADMIN']
    dbwalletzip_location = os.path.join(dbwallet_dir, object_name)
    if os.path.exists(dbwallet_dir):
        shutil.rmtree(dbwallet_dir)
    os.mkdir(dbwallet_dir)
    with open(dbwalletzip_location, 'w+b') as f:
        for chunk in obj.data.raw.stream(1024 * 1024, decode_content=False):
            f.write(chunk)
    with ZipFile(dbwalletzip_location, 'r') as zipObj:
        zipObj.extractall(dbwallet_dir)

def dbconnect(dbuser, dbpwd, dbsvc):
    try:
        dbconnection = cx_Oracle.connect(
            dbuser, dbpwd, dbsvc, encoding="UTF-8")
    except cx_Oracle.DatabaseError as e:
        raise
    return dbconnection

def get_dbinfo(dbconnection):
    dbcursor = dbconnection.cursor()
    dbcursor.execute(
        "select DBID, NAME, CREATED, LOG_MODE, OPEN_MODE, DATABASE_ROLE, PLATFORM_NAME, DB_UNIQUE_NAME, CDB from v$database")
    columns = (
        "DBID", "NAME", "CREATED", "LOG_MODE", "OPEN_MODE", "DATABASE_ROLE", "PLATFORM_NAME", "DB_UNIQUE_NAME", "CDB")
    values = dbcursor.fetchone()
    dbinfo = dict(zip(columns, values))
    dbcursor.execute("select sysdate from dual")
    today, = dbcursor.fetchone()
    dbinfo["SYSDATE"] = today
    dbcursor.execute("select MACHINE from v$session")
    client_host, = dbcursor.fetchone()
    dbinfo["CLIENT_HOST"] = client_host
    return dbinfo

def handler(ctx, data: io.BytesIO = None):
    try:
        body = json.loads(data.getvalue())
        dbuser = body.get("dbuser")
        dbpwd = body.get("dbpwd")
        dbsvc = body.get("dbsvc")
        dbwallet_bucket = body.get("dbwallet_bucket")
        dbwallet_object = body.get("dbwallet_object")
    except (Exception, ValueError) as ex:
        print(str(ex))

    get_dbwallet(dbwallet_bucket, dbwallet_object)
    dbconnection = dbconnect(dbuser, dbpwd, dbsvc)
    dbinfo = get_dbinfo(dbconnection)
    dbconnection.close()

    return response.Response(
        ctx,
        response_data=json.dumps(dbinfo, indent = 2, default=str),
        headers={"Content-Type": "application/json"}
    )
