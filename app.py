from flask import Flask, render_template, request, redirect, jsonify
import mysql.connector
import mysql.connector.pooling
import subprocess
import os
import signal
import logging
from mysql.connector import Error
import uuid

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Database connection pool configuration
DB_CONFIG = {
    'host': '82.180.144.17',
    'user': 'ip',
    'password': 'admin@1234#',
    'database': 'IP_satish_sir',
    'pool_name': 'mypool',
    'pool_size': 5
}

# Initialize connection pool
db_pool = mysql.connector.pooling.MySQLConnectionPool(**DB_CONFIG)

# Global process reference
script_process = None

def get_db_connection():
    try:
        conn = db_pool.get_connection()
        return conn
    except Error as e:
        app.logger.error(f"Database connection error: {str(e)}")
        raise

def validate_url_form(data):
    required_fields = ['url', 'target', 'unique', 'repeated']
    return all(data.get(field) for field in required_fields)

def validate_device_form(data):
    required_fields = ['adb_id', 'asset_no', 'state']
    return all(data.get(field) for field in required_fields)

@app.route('/', methods=['GET', 'POST'])
def index():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            if 'add_url' in request.form:
                if not validate_url_form(request.form):
                    app.logger.warning("Invalid URL form data")
                    return jsonify({'error': 'Missing required URL fields'}), 400

                try:
                    target = int(request.form['target'])
                    unique = float(request.form['unique'])
                    repeated = float(request.form['repeated'])
                    campaign_name = request.form.get('campaign_name', '')

                    cursor.execute("""
                        INSERT INTO url_clicks (url, target_clicks, unique_percent, repeated_percent, campaign_name)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (request.form['url'], target, unique, repeated, campaign_name))
                    conn.commit()
                    app.logger.info(f"Added new URL: {request.form['url']} with campaign: {campaign_name}")
                except ValueError as e:
                    app.logger.error(f"Invalid number format: {str(e)}")
                    return jsonify({'error': 'Invalid number format in form'}), 400

            if 'add_device' in request.form:
                if not validate_device_form(request.form):
                    app.logger.warning("Invalid device form data")
                    return jsonify({'error': 'Missing required device fields'}), 400

                cursor.execute("""
                    INSERT INTO device (adb_id, asset_no, state)
                    VALUES (%s, %s, %s)
                """, (request.form['adb_id'], request.form['asset_no'], request.form['state']))
                conn.commit()
                app.logger.info(f"Added new device: {request.form['adb_id']}")

            return redirect('/')

        # Ensure required columns exist
        cursor.execute("ALTER TABLE url_clicks ADD COLUMN IF NOT EXISTS is_selected BOOLEAN DEFAULT 0")
        cursor.execute("ALTER TABLE url_clicks ADD COLUMN IF NOT EXISTS campaign_name VARCHAR(255)")
        cursor.execute("ALTER TABLE device ADD COLUMN IF NOT EXISTS is_selected BOOLEAN DEFAULT 0")
        cursor.execute("ALTER TABLE device ADD COLUMN IF NOT EXISTS asset_no VARCHAR(100)")
        cursor.execute("ALTER TABLE device ADD COLUMN IF NOT EXISTS state VARCHAR(100)")
        conn.commit()

        cursor.execute("SELECT * FROM url_clicks")
        urls = cursor.fetchall()
        cursor.execute("SELECT * FROM device")
        devices = cursor.fetchall()

        return render_template("index.html", urls=urls, devices=devices)

    except Error as e:
        app.logger.error(f"Database error: {str(e)}")
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/toggle_device_selection/<int:id>', methods=['POST'])
def toggle_device_selection(id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT is_selected FROM device WHERE id = %s", (id,))
        device = cursor.fetchone()
        if not device:
            app.logger.warning(f"Device id {id} not found")
            return jsonify({'error': 'Device not found'}), 404

        new_state = 0 if device['is_selected'] else 1
        cursor.execute("UPDATE device SET is_selected = %s WHERE id = %s", (new_state, id))
        conn.commit()
        app.logger.info(f"Device id {id} selection toggled to {'selected' if new_state else 'deselected'}")
        return jsonify({'message': f"Device {'selected' if new_state else 'deselected'} successfully!"})
    except Error as e:
        app.logger.error(f"Database error toggling device id {id}: {str(e)}")
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/toggle_url_selection/<int:id>', methods=['POST'])
def toggle_url_selection(id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT is_selected FROM url_clicks WHERE id = %s", (id,))
        url = cursor.fetchone()
        if not url:
            app.logger.warning(f"URL id {id} not found")
            return jsonify({'error': 'URL not found'}), 404

        new_state = 0 if url['is_selected'] else 1
        cursor.execute("UPDATE url_clicks SET is_selected = %s WHERE id = %s", (new_state, id))
        conn.commit()
        app.logger.info(f"URL id {id} selection toggled to {'selected' if new_state else 'deselected'}")
        return jsonify({'message': f"URL {'selected' if new_state else 'deselected'} successfully!"})
    except Error as e:
        app.logger.error(f"Database error toggling URL id {id}: {str(e)}")
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/update_url/<int:id>', methods=['POST'])
def update_url(id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if not validate_url_form(request.form):
            app.logger.warning(f"Invalid URL update data for id {id}")
            return jsonify({'error': 'Missing required URL fields'}), 400

        try:
            target = int(request.form['target'])
            unique = float(request.form['unique'])
            repeated = float(request.form['repeated'])
            campaign_name = request.form.get('campaign_name', '')

            cursor.execute("""
                UPDATE url_clicks
                SET url = %s, target_clicks = %s, unique_percent = %s, repeated_percent = %s, campaign_name = %s
                WHERE id = %s
            """, (request.form['url'], target, unique, repeated, campaign_name, id))
            conn.commit()
            app.logger.info(f"Updated URL id {id}: {request.form['url']}")
            return jsonify({'message': 'URL updated successfully!'})
        except ValueError as e:
            app.logger.error(f"Invalid number format for URL id {id}: {str(e)}")
            return jsonify({'error': 'Invalid number format in form'}), 400
    except Error as e:
        app.logger.error(f"Database error updating URL id {id}: {str(e)}")
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/update_device/<int:id>', methods=['POST'])
def update_device(id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if not validate_device_form(request.form):
            app.logger.warning(f"Invalid device update data for id {id}")
            return jsonify({'error': 'Missing required device fields'}), 400

        cursor.execute("""
            UPDATE device
            SET adb_id = %s, asset_no = %s, state = %s
            WHERE id = %s
        """, (request.form['adb_id'], request.form['asset_no'], request.form['state'], id))
        conn.commit()
        app.logger.info(f"Updated device id {id}: {request.form['adb_id']}")
        return jsonify({'message': 'Device updated successfully!'})
    except Error as e:
        app.logger.error(f"Database error updating device id {id}: {str(e)}")
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/get_url/<int:id>', methods=['GET'])
def get_url(id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM url_clicks WHERE id = %s", (id,))
        url = cursor.fetchone()
        if not url:
            app.logger.warning(f"URL id {id} not found")
            return jsonify({'error': 'URL not found'}), 404
        return jsonify(url)
    except Error as e:
        app.logger.error(f"Database error fetching URL id {id}: {str(e)}")
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/get_device/<int:id>', methods=['GET'])
def get_device(id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM device WHERE id = %s", (id,))
        device = cursor.fetchone()
        if not device:
            app.logger.warning(f"Device id {id} not found")
            return jsonify({'error': 'Device not found'}), 404
        return jsonify(device)
    except Error as e:
        app.logger.error(f"Database error fetching device id {id}: {str(e)}")
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/used_devices', methods=['GET'])
def used_devices():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM device WHERE is_selected = 1 OR state = 'active'")
        devices = cursor.fetchall()
        return jsonify(devices)
    except Error as e:
        app.logger.error(f"Database error fetching used devices: {str(e)}")
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/used_urls', methods=['GET'])
def used_urls():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM url_clicks WHERE is_selected = 1")
        urls = cursor.fetchall()
        return jsonify(urls)
    except Error as e:
        app.logger.error(f"Database error fetching used URLs: {str(e)}")
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/delete_url/<int:id>', methods=['POST'])
def delete_url(id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT url FROM url_clicks WHERE id = %s", (id,))
        url = cursor.fetchone()
        if not url:
            app.logger.warning(f"URL id {id} not found")
            return jsonify({'error': 'URL not found'}), 404

        cursor.execute("DELETE FROM url_clicks WHERE id = %s", (id,))
        conn.commit()
        app.logger.info(f"Deleted URL id {id}: {url['url']}")
        return jsonify({'message': 'URL deleted successfully!'})
    except Error as e:
        app.logger.error(f"Database error deleting URL id {id}: {str(e)}")
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/delete_device/<int:id>', methods=['POST'])
def delete_device(id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT adb_id FROM device WHERE id = %s", (id,))
        device = cursor.fetchone()
        if not device:
            app.logger.warning(f"Device id {id} not found")
            return jsonify({'error': 'Device not found'}), 404

        cursor.execute("DELETE FROM device WHERE id = %s", (id,))
        conn.commit()
        app.logger.info(f"Deleted device id {id}: {device['adb_id']}")
        return jsonify({'message': 'Device deleted successfully!'})
    except Error as e:
        app.logger.error(f"Database error deleting device id {id}: {str(e)}")
        return jsonify({'error': 'Database error occurred'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/run-script', methods=['POST'])
def run_script():
    global script_process
    if script_process is None or script_process.poll() is not None:
        try:
            script_path = os.path.join(os.path.dirname(__file__), 'main_script.py')
            if not os.path.exists(script_path):
                app.logger.error("main_script.py not found")
                return jsonify({'message': 'Script file not found'}), 404

            script_process = subprocess.Popen([
                r'C:\Users\Admin\AppData\Local\Programs\Python\Python312\python.exe',
                script_path
            ])
            app.logger.info("Script started")
            return jsonify({'message': 'Script started successfully!'})
        except Exception as e:
            app.logger.error(f"Failed to start script: {str(e)}")
            return jsonify({'message': f'Failed to start script: {str(e)}'}), 500
    else:
        app.logger.warning("Attempted to start script while already running")
        return jsonify({'message': 'Script is already running!'}), 400

@app.route('/stop-script', methods=['POST'])
def stop_script():
    global script_process
    if script_process and script_process.poll() is None:
        try:
            os.kill(script_process.pid, signal.SIGTERM)
            script_process.wait(timeout=5)
            app.logger.info("Script stopped")
            return jsonify({'message': 'Script stopped successfully!'})
        except Exception as e:
            app.logger.error(f"Failed to stop script: {str(e)}")
            return jsonify({'message': f'Failed to stop script: {str(e)}'}), 500
    else:
        app.logger.warning("Attempted to stop non-running script")
        return jsonify({'message': 'No running script to stop!'}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)