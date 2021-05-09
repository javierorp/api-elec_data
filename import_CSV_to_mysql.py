import argparse
import mysql.connector
import argparse
import csv
import datetime
import os

def arg_parser():
    """Parse the parameters entered by command line"""

    parser = argparse.ArgumentParser(description="This script imports the data from a csv passed by parameters to a DB")
    parser.add_argument('csv', help='File path and file name')
    args = parser.parse_args()

    return args.csv

def check_file(csv_file):
    """Check if the document exists"""

    if not os.path.isfile(csv_file):
        raise Exception("'{0}' file does not exist". format(csv_file))

def check_database(db_host = "localhost", db_user = "root", db_pass = "root"):
    """Check the database connection"""

    conn = mysql.connector.connect(host=db_host, user=db_user, passwd=db_pass)  
    print("OK - Database connection")

    return conn

def create_db_tables(db_name, db_table, conn):
    """Create a database, a table for that database and a default user table
    with a trigger and a default user to use the api
    """

    # Creating the cursor
    cursor = conn.cursor()

    # Creating the database
    cursor.execute("CREATE DATABASE IF NOT EXISTS {0} DEFAULT CHARACTER SET 'utf8';".format(db_name))
    print("OK - '{0}' database".format(db_name))

    # Creating the table
    table_cmd = ("CREATE TABLE IF NOT EXISTS {0}.{1}("
        " id INT NOT NULL AUTO_INCREMENT comment 'Row id',"
        " date DATETIME NOT NULL comment 'Date of consumption',"
        " energy DECIMAL(15, 5) comment 'Energy (kWh)',"
        " reactive_energy DECIMAL(15, 5) comment 'Reactive energy (kVArh)',"
        " power DECIMAL(15, 5) comment 'Power (kW)',"
        " maximeter DECIMAL(15, 5) comment 'Maximeter (kW)',"
        " reactive_power DECIMAL(15, 5) comment 'Reactive power (kVAr)',"
        " voltage DECIMAL(15, 5) comment 'Voltage (V)',"
        " intensity DECIMAL(15, 5) comment 'Intensity (A)',"
        " power_factor DECIMAL(15, 5) comment 'Power factor (Fi)',"
        " PRIMARY KEY (id)"
        " );".format(db_name, db_table))

    cursor.execute(table_cmd)
    cursor.execute("USE elecprod")
    print("OK - '{0}.{1}' table".format(db_name, db_table))

    # Creating default user table
    usertab_cmd = ("CREATE TABLE IF NOT EXISTS {0}.users("
        " id INT NOT NULL AUTO_INCREMENT comment 'Row id',"
        " user CHAR(10) comment 'Authorized user',"
        " password char(200) comment 'Password encoded in SHA1 256',"
        " PRIMARY KEY (id),"
        " UNIQUE KEY (user)"
        " );".format(db_name))
    
    cursor.execute(usertab_cmd)
    print("OK - '{0}.{1}' table".format(db_name, "users"))

    # Drop trigger if exists
    cursor.execute("DROP TRIGGER IF EXISTS {0}.encpassword;".format(db_name))
    
    # Creating trigger
    trigger_cmd = ("CREATE TRIGGER encpassword BEFORE INSERT ON {0}.users"
        " FOR EACH ROW SET NEW.password = SHA2(NEW.password, 256);".format(db_name))

    cursor.execute(trigger_cmd)
    print("OK - Trigger")

    # Creating user
    cursor.execute("INSERT INTO elecprod.users(user, password)VALUES('rick', 'morty');")
    print("OK - User")

    conn.commit()
    cursor.close()

def create_or_user(host, db_name, user, passw):
    """Create an only-read user for an entire database"""

    cursor = conn.cursor()

    # Creating user
    cursor.execute("CREATE USER IF NOT EXISTS '{0}'@'{1}' IDENTIFIED BY '{2}';".format(user, host, passw))

    # Read-only privileges over the entire database from any host
    cursor.execute("GRANT SELECT, SHOW VIEW ON {0}.* TO '{1}'@'{2}';".format(db_name, user, host))
    cursor.execute("FLUSH PRIVILEGES;")

    # Cheking the new user
    newconn = check_database(host, user, passw)
    newcursor = newconn.cursor()
    newcursor.execute("select 2021 from dual;")
    result = newcursor.fetchone()
    if result[0] == 2021:
        print("OK - '{0}' user".format(user))
    else:
        raise Exception("Some error happened when creating '{0}' user".format(user))

    cursor.close()
    newcursor.close()
    newconn.close()

def csv_2_db(csv_file, db_name, db_table, conn):
    """Reads the csv file and inserts it into the database"""

    cursor = conn.cursor()

    with open(csv_file, 'r') as csvfile:
        line = 0
        try:
            reader = csv.reader(csvfile, delimiter=',')
            
            for idx, row in enumerate(reader):
                line = idx + 1
                if idx == 0:
                    if len(row) != 9:
                        raise Exception("The csv format does not match with the expected one")
                else:
                    date = datetime.datetime.strptime(row[0], "%d %b %Y %H:%M:%S")
                    date.strftime("%Y-%m-d %H:M:%S")
                
                    insert = ("insert into {0}.{1}"
                        "(date, energy, reactive_energy, power, maximeter, reactive_power, voltage, intensity, power_factor)"
                        "values("
                        "STR_TO_DATE('{2}', '%Y-%m-%d %T'), {3}, {4}, {5}, {6}, {7}, {8}, {9}, {10});".format(db_name, db_table, date, row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8])
                        )

                    # Replacing empty values by null
                    insert = insert.replace(" ,", " NULL,").replace(", );", ", NULL);")
        
                    cursor.execute(insert)
                    print("Importing line {0}".format(line), end="\r")
            
            conn.commit()
            print("OK - CSV ({0} lines) successfully imported to {1}.{2}".format(line-1, db_name, db_table))

        except Exception as err:
            conn.rollback()
            raise Exception("Could not insert the values of row {0}: {1}".format(line, err))
        finally:
            cursor.close()

if __name__ == "__main__":
    try:
        # Database connection info
        db_host = "localhost"
        db_user = "root"
        db_pass = "admin"

        # Database names
        db_name = "elecprod"
        db_table = "consumpdata"
        db_oruser = "blue" # Only-read user
        db_oruser_pass = "blue21" # Only-read user password
        db_oruser_host = "localhost" # Only-read user host
        
        conn = "" # DB connection
        csv_file = arg_parser()
        check_file(csv_file) # Check if the file exists
        conn = check_database(db_host, db_user, db_pass) # Make a db connection
        create_db_tables(db_name, db_table, conn) # Create database, tables and api user
        create_or_user(db_oruser_host, db_name, db_oruser, db_oruser_pass) # Create database only-read user
        csv_2_db(csv_file, db_name, db_table, conn) # Insert all records in db

    except KeyboardInterrupt:
        if type(conn) is not str and conn.is_connected():
            conn.rollback()
        print("Program stopped")
    except Exception as e:
        print("ERROR - {0}".format(e))
    finally:
        if type(conn) is not str and conn.is_connected():
            conn.close()
