# API Electricity data

**Author:** Javier Orti Priego ([javierorp](https://www.linkedin.com/in/javierortipriego/))

A Spanish version of this document is available [here](https://github.com/javierorp/api-elec_data/blob/main/README_es.md).

Development of a script to import CSV data into a database and a REST API (made with Flask and Flask-RESTPlus) that allows access to this data. The API is secured and saves requests in cache memory for 10 min. Tests are included to verify the correct access to the database with the imported data and the operation of the API.

   * [Index](#api-electricity-data)
      * [Requirements](#requirements)
      * [Available files](#available-files)
      * [import_CSV_to_mysql.py](#import_csv_to_mysqlpy)
      * [api.py](#apipy)
         * [/login](#login)
         * [/ (Swagger)](#-swagger)
         * [/apielec/ping](#apielecping)
         * [/apielec/getData](#apielecgetdata)
         * [/apielec/getDataById](#apielecgetdatabyid)
         * [/apielec/getDataByDate](#apielecgetdatabydate)
         * [/apielec/getDataByRange](#apielecgetdatabyrange)
      * [test.py](#testpy)
      * [Troubleshooting](#troubleshooting)
         * [PyJWT and Werkzeug](#pyjwt-and-werkzeug)

## Requirements

- [MySQL Community Server 8.0.24](https://downloads.mysql.com/archives/installer/)
- [Python 3.9.5](https://www.python.org/downloads/release/python-395/)
- Required Python packages:
  - mysql-connector-python==8.0.24
  - Flask==1.1.2
  - Flask-Caching==1.10.1
  - flask-restplus==0.13.0
  - Werkzeug==0.16.1
  - PyJWT==2.1.0

You can use the *requirements.txt* file to install the packages:

```powershell
PS > pip install -r requirements.txt
```

or if you want to install it in a virtual environment:

```powershell
PS > pipenv install -r requirements.txt
```

What is described here has been tested and developed on Windows 10 Home (version 20H2, build 19042.964).

## Available files

- **requirements.txt:** it contains the python packages needed to import the data and run the API.
- **Monitoring_report.csv:** it contains the data to be imported into the database and used by the API.
- **import_CSV_to_mysql.py:** script to import the data from the CSV file *Monitoring_report.csv* to be passed as an argument. Create the database, tables and user needed to make use of the API.
- **api.py:** raises the API so that it can be used on port 5000. It has debug mode enabled.
- **test.py**: it contains 8 unit tests that check both if the database is created correctly and if the API responds as it should.

## import_CSV_to_mysql.py

This script imports the data from *Monitoring_report.csv*, for which it creates a database called *elecprod* and a table *consumpdata*, where the data will be dumped. It also creates a table of users, named as *users*, which will be the users that can access the API, a trigger so that all the passwords are not stored in plain text, but the SHA1 256 hash they produce is stored, and inserts a *rick* user with a *morty* password in this table. Finally, to access the database and be able to make queries, create a read-only user (it can only make *select*) on *elecprod* database, with name *blue* and password *blue21*, on the local machine.

The local database is accessed with *root* user and *admin* password, so if they are different, they must be changed in the script (*db_user* and *db_pass* variables).

The SQL statements executed by this script are as follows:

```sql
-- Database creation
CREATE DATABASE IF NOT EXISTS elecprod DEFAULT CHARACTER SET 'utf8';

-- Table creation
CREATE TABLE IF NOT EXISTS elecprod.consumpdata (
    id INT NOT NULL AUTO_INCREMENT COMMENT 'Row id',
    date DATETIME NOT NULL COMMENT 'Date of consumption',
    energy DECIMAL(15 , 5 ) COMMENT 'Energy (kWh)',
    reactive_energy DECIMAL(15 , 5 ) COMMENT 'Reactive energy (kVArh)',
    power DECIMAL(15 , 5 ) COMMENT 'Power (kW)',
    maximeter DECIMAL(15 , 5 ) COMMENT 'Maximeter (kW)',
    reactive_power DECIMAL(15 , 5 ) COMMENT 'Reactive power (kVAr)',
    voltage DECIMAL(15 , 5 ) COMMENT 'Voltage (V)',
    intensity DECIMAL(15 , 5 ) COMMENT 'Intensity (A)',
    power_factor DECIMAL(15 , 5 ) COMMENT 'Power factor (Fi)',
    PRIMARY KEY (id)
);

-- Creation of the table with the users who can access the API
CREATE TABLE IF NOT EXISTS elecprod.users (
    id INT NOT NULL AUTO_INCREMENT COMMENT 'Row id',
    user CHAR(10) COMMENT 'Authorized user',
    password CHAR(200) COMMENT 'Password encoded in SHA1 256',
    PRIMARY KEY (id),
    UNIQUE KEY (user)
);

-- Deletion of the trigger if it already exists
DROP TRIGGER IF EXISTS elecprod.encpassword;

-- Creation of the trigger that encrypts passwords
CREATE 
    TRIGGER  encpassword
 BEFORE INSERT ON elecprod.users FOR EACH ROW 
    SET NEW . password = SHA2(NEW.password, 256);

-- Creation of the API access user
INSERT INTO elecprod.users(user, password)VALUES('rick', 'morty');

-- Creation of the DB read-only user and permissions assignment
CREATE USER IF NOT EXISTS 'blue'@'localhost' IDENTIFIED BY 'blue21';
GRANT SELECT, SHOW VIEW ON elecprod.* TO 'blue'@'localhost';
```

As you can see in the creation code of the *consumpdata* table, an auto incremental id is included that acts as a primary key, as in the *users* table, where, in addition to the id that is the primary key, the *user* field is included as a unique key, so that there cannot be two users with the same name.

Script execution:

```powershell
PS > python import_CSV_to_mysql.py Monitoring_report.csv
OK - Database connection
OK - 'elecprod' database
OK - 'elecprod.consumpdata' table
OK - 'elecprod.users' table
OK - Trigger
OK - User
OK - Database connection
OK - 'blue' user
OK - CSV (11716 lines) successfully imported to elecprod.consumpdata
```

## api.py

It is a REST API made with Flask and Flask-RESTPlus, it is secured and has a cache of 10 minutes. The choice of making a REST API is for ease of use because, regardless of the programming language used, it can be accessed by only POST and GET requests.

Flask is a minimalist Python framework for creating web applications that is easy to implement, resource-efficient and free to use. Flask-RESTPlus is an extension of Flask to build APIs and to implement Swagger. The main function of this API is to access the information contained in the *consumpdata* table of the *elecprod* database.

To run the api:

```powershell
PS> python api.py
2021-05-09 15:09:37.150 INFO api - check_database: Database connection OK
 * Serving Flask app "api" (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: on
2021-05-09 15:09:37.165 INFO _internal - _log:  * Restarting with stat
2021-05-09 15:09:37.759 INFO api - check_database: Database connection OK
2021-05-09 15:09:37.775 WARNING _internal - _log:  * Debugger is active!
2021-05-09 15:09:37.775 INFO _internal - _log:  * Debugger PIN: 180-314-403
2021-05-09 15:09:37.790 INFO _internal - _log:  * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)

```

The API, as shown in the last line, is running on our machine (127.0.0.1) on port 5000. Before being available, it checks that it can access the database and obtains from it the columns of the *consumpdata* table, which will be used in the request responses.

The following addresses are available:

```json
/
|-login
|-apielec
	|-ping
	|-getData
	|-getDataById
	|-getDataByDate
	|-getDataByRange
```

With the exception of "login", all the functions depend on "apielec". Similarly, all of them allow GET requests except "login" (although it allows it on a test version).

### /login

In order to access the API it is necessary to obtain a token that will be used as API Key. To do this, we need to make a POST request to the address http://127.0.0.1:5000/login with authorization type "Basic Auth", user "rick" and password "morty".

Although in a real environment the requests would be made directly from another application, to test it from the browser, if you do not want to use applications to make requests such as Postman, GET requests are allowed, which means that the browser will open a pop-up window requesting the user and password.

If the request is invalid it will return:

```json
{
  "message": "Invalid user and/or password", 
  "status": "ERROR", 
  "statusCode": "401"
}
```

And whether it is correct:

```json
{
  "Authorization_type": "API Key", 
  "In": "header", 
  "Key": "SESSION", 
  "value_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoicmljayJ9.jVk2x58TIaYxetUSLO_wfFk4BkI9saTtCPU8KD8DaQM"
}
```

The token obtained will be the one to be used for requests to the API, where **authorisations should be of type "API KEY", with key "SESSION", value the token obtained and added to the header of the request**. Once the API is accessed with the obtained token, it is stored indefinitely in memory until the API is restarted.

### / (Swagger)

In the main directory of the API we can see the documentation. Thus, accessing the address http://127.0.0.1:5000/ from our browser shows all accessible API requests, with a short description of each one of them, the parameters they accept and the responses they return.

As the API is secured, although you can see the documentation, you cannot make requests. To allow requests to be sent, we need to click on "Authorize" (top right) and enter our token. With this, we could then launch requests directly from Swagger.

If we make requests without authentication we will get:

```json
{
  "status": "Token is missing",
  "statusCode": "405"
}
```

On the opposite, if the token is wrong, we will get:

```json
{
  "status": "Token is invalid",
  "statusCode": "406"
}
```

### /apielec/ping

It only checks if the API is accessible and running correctly. Making a GET request to the address http://127.0.0.1:5000/apielec/ping correctly authenticated, the following response is obtained:

```json
{
    "message": "I'm here!!",
    "status": "OK",
    "statusCode": 200,
    "values": {
        "numrecs": 0,
        "records": []
    }
}
```

### /apielec/getData

| Parameters | Type | Description |
| ---------- | ---- | ----------- |
| -          | -    | -           |

| Response (code) | Description      |
| --------------- | ---------------- |
| 200             | OK               |
| 405             | Token is missing |
| 406             | Invalid token    |

It obtains all the data available in the database. So when a GET request is made to the address http://127.0.0.1:5000/apielec/getData correctly authenticated, the query to the database is as follows:

```sql
SELECT * FROM elecprod.consumpdata;
```

getting the answer:

```json
{
    "message": "",
    "status": "OK",
    "statusCode": 200,
    "values": {
        "numrecs": 11716,
        "records": [
            {
                "date": "2019-08-01 00:00:00",
                "energy": "1.21100",
                "id": "1",
                "intensity": "53.00300",
                "maximeter": "5.30600",
                "power": "5.15600",
                "power_factor": "0.85700",
                "reactive_energy": "0.20000",
                "reactive_power": "-8.38200",
                "voltage": "121.95500"
            },
            {
                "date": "2019-08-01 00:15:00",
                "energy": "1.29900",
                "id": "2",
                "intensity": "57.35200",
                "maximeter": "6.21500",
                "power": "5.29700",
                "power_factor": "0.04700",
                "reactive_energy": "0.30000",
                "reactive_power": "-8.29500",
                "voltage": "121.13500"
            },
            ...           
        ]
    }
}
```

### /apielec/getDataById

| Parameters | Type   | Description                                                  |
| ---------- | ------ | ------------------------------------------------------------ |
| id         | string | Specifies the Id associated with the record. Accepts multiple identifiers separated by commas (e.g. 1,2,3). |

| Response (code) | Description       |
| --------------- | ----------------- |
| 200             | OK                |
| 400             | Invalid argument  |
| 405             | Token is missing  |
| 406             | Invalid token     |
| 500             | Mapping Key Error |

Gets all records whose identifier(s) (separated by commas, e.g. 1,2,3) it finds in the reference table. Accepts the parameter to be both in the request header and in the body in json format. Making a GET request to the address http://127.0.0.1:5000/apielec/getDataById correctly authenticated, the query to the database is as follows:

```sql
SELECT * FROM elecprod.consumpdata where id in ({id});
```

For example, for the request http://127.0.0.1:5000/apielec/getDataById?id=5,100, you obtain:

```json
{
    "message": "",
    "status": "OK",
    "statusCode": 200,
    "values": {
        "numrecs": 2,
        "records": [
            {
                "date": "2019-08-01 01:00:00",
                "energy": "1.71000",
                "id": "5",
                "intensity": "78.31200",
                "maximeter": "14.64400",
                "power": "9.42300",
                "power_factor": "0.86900",
                "reactive_energy": "0.61000",
                "reactive_power": "-10.10200",
                "voltage": "122.01000"
            },
            {
                "date": "2019-08-02 00:45:00",
                "energy": "3.20100",
                "id": "100",
                "intensity": "93.34600",
                "maximeter": "14.15700",
                "power": "11.44800",
                "power_factor": "0.07300",
                "reactive_energy": "0.20000",
                "reactive_power": "-13.40000",
                "voltage": "121.33500"
            }
        ]
    }
}
```

### /apielec/getDataByDate

| Parameters | Type   | Description                                                  |
| ---------- | ------ | ------------------------------------------------------------ |
| date       | string | The date and time will be searched in the format "YYYYY-MM-DD HH:MM:SS". It accepts the "%" sign and the "_" sign. |

| Response (code) | Description       |
| --------------- | ----------------- |
| 200             | OK                |
| 400             | Invalid argument  |
| 405             | Token is missing  |
| 406             | Invalid token     |
| 500             | Mapping Key Error |

found in the reference table. It accepts that the parameter is both in the header of the request and in the body in json format. Making a GET request to the address http://127.0.0.1:5000/apielec/getDataByDate correctly authenticated, the query to the database is as follows:

```sql
SELECT * FROM elecprod.consumpdata where date like '{date}');
```

For example, for the request http://127.0.0.1:5000/apielec/getDataByDate?date=2019-09-11_0_:00:00, you obtain:

```json
{
    "message": "",
    "status": "OK",
    "statusCode": 200,
    "values": {
        "numrecs": 10,
        "records": [
            {
                "date": "2019-09-11 00:00:00",
                "energy": "5.80000",
                "id": "3937",
                "intensity": "129.17500",
                "maximeter": "23.35100",
                "power": "23.21600",
                "power_factor": "0.87300",
                "reactive_energy": "0.00000",
                "reactive_power": "-16.68200",
                "voltage": "185.96900"
            },
            {
                "date": "2019-09-11 01:00:00",
                "energy": "4.50000",
                "id": "3941",
                "intensity": "89.68300",
                "maximeter": "20.32200",
                "power": "17.23900",
                "power_factor": "0.89800",
                "reactive_energy": "0.20000",
                "reactive_power": "-7.56100",
                "voltage": "186.71100"
            },
            ...
        ]
    }
}
```

### /apielec/getDataByRange

| Parameters | Type   | Description                                                  |
| ---------- | ------ | ------------------------------------------------------------ |
| date       | string | Initial date and time in the format 'YYYYY-MM-DD HH:MM:SS' to search for. Accepts the '%' sign and the '_' sign. |
| end_date   | string | End date and time in the format 'YYYYY-MM-DD HH:MM:SS' to search for. Accepts the '%' sign and the '_' sign. |

| Response (code) | Description       |
| --------------- | ----------------- |
| 200             | OK                |
| 400             | Invalid argument  |
| 405             | Token is missing  |
| 406             | Invalid token     |
| 500             | Mapping Key Error |

Gets all records with a date between the two dates specified in the request that it finds in the reference table. It accepts that the parameter is both in the request header and in the body in json format. Making a GET request to the address http://127.0.0.1:5000/apielec/getDataByRange correctly authenticated, the query to the database is as follows:

```sql
SELECT * FROM elecprod.consumpdata where date between '{date}' and '{end_date}');
```

For example, for the request http://127.0.0.1:5000/apielec/getDataByRange?date=2019-09-12_10:00:00&end_date=2019-09-12_10:30:00, you obtain:

```json
{
    "message": "",
    "status": "OK",
    "statusCode": 200,
    "values": {
        "numrecs": 3,
        "records": [
            {
                "date": "2019-09-12 10:00:00",
                "energy": "0.89900",
                "id": "4073",
                "intensity": "18.77900",
                "maximeter": "4.12500",
                "power": "3.53700",
                "power_factor": "0.95700",
                "reactive_energy": "0.60000",
                "reactive_power": "2.39500",
                "voltage": "184.09600"
            },
            {
                "date": "2019-09-12 10:15:00",
                "energy": "1.30100",
                "id": "4074",
                "intensity": "37.31300",
                "maximeter": "11.75800",
                "power": "6.65800",
                "power_factor": "0.95200",
                "reactive_energy": "1.00000",
                "reactive_power": "5.20600",
                "voltage": "183.93800"
            },
            {
                "date": "2019-09-12 10:30:00",
                "energy": "2.69900",
                "id": "4075",
                "intensity": "64.51200",
                "maximeter": "11.58000",
                "power": "10.53400",
                "power_factor": "0.95200",
                "reactive_energy": "1.09900",
                "reactive_power": "-1.08700",
                "voltage": "183.78300"
            }
        ]
    }
}
```

## test.py

This script includes 8 unit tests that check in order:

1. The database can be accessed correctly with the read-only user.
2. The read-only user can not insert data.
3. The API returns an error when trying to login with incorrect credentials.
4. With the correct credentials the API returns a valid token.
5. Correct data is received when calling /apielec/getData.
6. Correct data is received when calling /apielec/geById.
7. Correct data is received when calling /apielec/getDataByDate
8. Correct data is received when calling /apielec/getDataByRange

To run the test:

```powershell
PS > python test.py
........
----------------------------------------------------------------------
Ran 8 tests in 0.246s

OK
```

## Troubleshooting

### PyJWT and Werkzeug

If the API does not generate tokens correctly or it is impossible to generate them, it may be because the version of the Werkzeug package is incompatible with the version of PyJWT installed. To fix this, you have to install the versions listed in the requirements, i.e. 0.16.1 for Werkzeug and 2.1.0 for PyJWT.

```powershell
PS > pip unistall werkzeug
PS > pip install werkzeug==0.16.1

PS > pip unistall pyjwt
PS > pip install pyjwr==2.1.0
```

