from flask import Flask, jsonify, request, make_response
from flask_restplus import Api, Resource, reqparse
from functools import cache, wraps
from flask_caching import Cache
from functools import wraps
from json import loads
import mysql.connector
import logging
import urllib
import jwt

# Flask
app = Flask(__name__)
config= {
    "RESTPLUS_VALIDATE": True,
    "SECRET_KEY": "javierorp2021",
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 600 # 10 min
}
app.config.from_mapping(config)
cache = Cache(app)

# Swagger
authorizations = {
    "apikey": {
        "type": "apiKey",
        "in": "header",
        "name": "SESSION"
    }
}
api = Api(app, version="1.0", title="API Electricity data",
    description="Get electricity data from server.\nAuthor: Javier Orti Priego (javierorp)",
    authorizations=authorizations)
name_space = api.namespace('apielec', description='APIs to get electricity data from server.')

# Expected call parameters.
parserId = reqparse.RequestParser()
parserId.add_argument("id", type=str, help="Specifies the Id associated with the record. Accepts multiple identifiers separated by commas.")
parserDate = reqparse.RequestParser()
parserDate.add_argument("date", type=str, help="Date and time in the format 'YYYY-MM-DD HH:MM:SS' to be searched. Accepts '%' sign and '_' sign.")
parserRange = reqparse.RequestParser()
parserRange.add_argument("date", type=str, help="Initial date and time in the format 'YYYY-MM-DD HH:MM:SS' to be searched. Accepts '%' sign and '_' sign.")
parserRange.add_argument("end_date", type=str, help="End date and time in the format 'YYYY-MM-DD HH:MM:SS' to be searched. Accepts '%' sign and '_' sign.")


conn = "" # DB connection
columns = [] # Columns in db_tab
tokens = [] # Tokens allowed

# Database connection info
db_host = "localhost"
db_user = "blue"
db_pass = "blue21"
db_name = "elecprod"
db_tab = "consumpdata"


@app.route("/login", methods=["GET", "POST"])
def loging():
    """Checks that the user and password are valid and returns a token to be used"""
    auth = request.authorization
    
    if auth is not None and check_user(auth):
            token = jwt.encode({"user": auth.username}, app.config["SECRET_KEY"], algorithm="HS256")
            if token not in tokens:
                tokens.append(token)

            return jsonify({"Authorization_type": "API Key", "Key": "SESSION", "In": "header", "value_token": token})
    
    return make_response(jsonify({"status": "ERROR", "statusCode": "401", "message": "Invalid user and/or password"})), 401, {"WWW-Authenticate": "Basic realm='Login Required'"}

def token_required(f):
    """Require a valid token to use the api"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if "SESSION" in request.headers:
            token = request.headers["SESSION"]
        
        if not token:
            name_space.abort(405, status = "Token is missing", statusCode = "405")
        
        if token not in tokens:
            name_space.abort(406, status = "Invalid token", statusCode = "406")
        
        return f(*args, **kwargs)

    return decorated

def cache_key():
    """Allow to cache the solution."""
    try:
        args = request.get_json()
        if args is None:
            args = dict(request.args)
        
        key = request.path
        if  args:
            key += '?' + urllib.parse.urlencode([
                (k, v) for k in sorted(args) for v in args[k]
            ])
        return key

    except KeyError as err:
         name_space.abort(500, status = "Unable to obtain the data", statusCode = "500")
        
    except Exception as err:
        logging.error(err)
        name_space.abort(400, status = "Unable to obtain the data", statusCode = "400")


@name_space.route("/ping") # /apielec/ping
class Ping(Resource):
    @api.doc(responses={ 200: 'OK', 400: 'Invalid argument', 500: 'Mapping Key Error', 405: 'Token is missing', 406: 'Invalid token' })
    @api.doc(security='apikey')
    @token_required
    def get(self):
            """Check if the server is responding."""
            return format_result(status="OK", msg="I'm here!!")

@name_space.route("/getData") # /apielec/getData
class GetData(Resource):
    @api.doc(responses={ 200: 'OK', 405: 'Token is missing', 406: 'Invalid token' })
    @api.doc(security='apikey')
    @token_required
    @cache.cached(key_prefix=cache_key)
    def get(self):
        """Get all the records in the database."""
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM {0}.{1};".format(db_name, db_tab))
            rows = cursor.fetchall()
            cursor.close()

            return format_result(status="OK", msg="", rows=rows)
            
        except KeyError as err:
            name_space.abort(500, err.__doc__, status = "Unable to obtain the data", statusCode = "500")
        
        except Exception as err:
            logging.error(err)
            name_space.abort(400, err.__doc__, status = "Unable to obtain the data", statusCode = "400")


@name_space.route("/getDataById") # /apielec/getDataById
class GetDataById(Resource):
    @api.doc(responses={ 200: 'OK', 400: 'Invalid argument', 500: 'Mapping Key Error', 405: 'Token is missing', 406: 'Invalid token' })
    @api.doc(security='apikey')
    @token_required
    @name_space.expect(parserId)
    @cache.cached(key_prefix=cache_key)
    def get(self):
        """Get all records in the database that match the id or identifiers.
        Accepts multiple identifiers separated by commas. Eg: "1,2,3,4".
        """
        try:
            args = parserId.parse_args(strict=True)
            id = args["id"]
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM {0}.{1} where id in ({2});".format(db_name, db_tab, id))
            rows = cursor.fetchall()
            cursor.close()

            return format_result(status="OK", msg="", rows=rows)
            
        except KeyError as err:
            name_space.abort(500, err.__doc__, status = "Unable to obtain the data", statusCode = "500")
        
        except Exception as err:
            logging.error(err)
            name_space.abort(400, err.__doc__, status = "Unable to obtain the data", statusCode = "400")


@name_space.route("/getDataByDate") # /apielec/getDataByDate
class GetDataByDate(Resource):
    @api.doc(responses={ 200: 'OK', 400: 'Invalid argument', 500: 'Mapping Key Error', 405: 'Token is missing', 406: 'Invalid token' })
    @api.doc(security='apikey')
    @token_required
    @name_space.expect(parserDate)
    @cache.cached(key_prefix=cache_key)
    def get(self):
        """Get all records in the database that match the date.
        Accepts '%' sign and '_' sign.
        """
        try:
            args = parserDate.parse_args(strict=True)
            date = args["date"]
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM {0}.{1} where date like '{2}';".format(db_name, db_tab, date))
            rows = cursor.fetchall()
            cursor.close()

            return format_result(status="OK", msg="", rows=rows)

        except KeyError as err:
            name_space.abort(500, err.__doc__, status = "Unable to obtain the data", statusCode = "500")
        
        except Exception as err:
            logging.error(err)
            name_space.abort(400, err.__doc__, status = "Unable to obtain the data", statusCode = "400")


@name_space.route("/getDataByRange") # /apielec/getDataByRange
class GetDataByRange(Resource):
    @api.doc(responses={ 200: 'OK', 400: 'Invalid argument', 500: 'Mapping Key Error', 405: 'Token is missing', 406: 'Invalid token' })
    @api.doc(security='apikey')
    @token_required
    @name_space.expect(parserRange)
    @cache.cached(key_prefix=cache_key)
    def get(self):
        """Get all records in the database that match between the given dates.
        Accepts '%' sign and '_' sign.
        """
        try:
            args = parserRange.parse_args(strict=True)
            date = args["date"]
            end_date = args["end_date"]
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM {0}.{1} where date between '{2}' and '{3}';".format(db_name, db_tab, date, end_date))
            rows = cursor.fetchall()
            cursor.close()

            return format_result(status="OK", msg="", rows=rows)

        except KeyError as err:
            name_space.abort(500, err.__doc__, status = "Unable to obtain the data", statusCode = "500")
        
        except Exception as err:
            logging.error(err)
            name_space.abort(400, err.__doc__, status = "Unable to obtain the data", statusCode = "400")


def format_result(status, msg="", rows=""):
    """Provide a specific format for responding to the request. Returns the formatted response."""
    try:
        result = {
            "status": status,
            "statusCode": 200,
            "message": msg,
            "values": { "numrecs": len(rows), "records": []}
        }

        if len(rows) > 0:
            for row in rows:
                record = "{"
                for idx, col in enumerate(columns):
                    record += '"{0}": "{1}",'.format(col, row[idx])
                record = record[:-1]
                record += "}"
                result['values']['records'].append(loads(record))
        else:
            if type(rows) is list:
                result["message"] = "No data found"

        return jsonify(result)
                    
    except Exception as err:
        logging.error(err)
        name_space.abort(400, err.__doc__, status = "Unable to obtain the data", statusCode = "400")



def get_columns():
    """Obtain the columns of the reference table"""

    cursor = conn.cursor()
    cursor.execute("select column_name from information_schema.columns"
        " where table_schema = '{0}'"
        " and table_name = '{1}'"
        " order by table_name, ordinal_position".format(db_name, db_tab))
    cols = cursor.fetchall()

    for col in cols:
        columns.append(col[0])

    cursor.close()


def check_database(db_host = "localhost", db_user = "user", db_pass = "pass"):
    """Check the database connection. Returns the connection."""

    conn = mysql.connector.connect(host=db_host, user=db_user, passwd=db_pass, database=db_name)  
    logging.info("Database connection OK")

    return conn

def check_user(auth):
    """Check if authorised. Returns true or false"""

    cursor = conn.cursor()
    cursor.execute("SELECT CASE"
	" when SHA2('{0}', 256) = password then true"
    " else false end as result"
    " from elecprod.users where user = '{1}';".format(auth.password, auth.username))
    ret = cursor.fetchone()
    cursor.close()

    if ret is None:
        return False
    elif ret[0] == 1:
        return True
    else:
        return False


if __name__ == "__main__":
    try:
        # Logging configuration
        logging.basicConfig(level=logging.INFO,
            format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')
        
        # Check if database connection is available
        conn = check_database(db_host, db_user, db_pass)

        # Get columns of the reference table to use in the response
        get_columns()

        # 
        app.run(debug=True, port=5000)

    except KeyboardInterrupt:
        logging.info("Program stopped")
    except Exception as e:
        logging.error("ERROR - {0}".format(e))
    finally:
        if type(conn) is not str and conn.is_connected():
            conn.close()