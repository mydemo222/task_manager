# app.py
from flask import Flask, request, render_template, redirect, url_for, flash, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
import time

app = Flask(__name__)
app.secret_key = "mysecretkeyfordevonly12345"  # Not a good practice for production

# Database initialization
def get_db_connection():
    conn = sqlite3.connect('tasks.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        due_date TEXT,
        status TEXT DEFAULT 'pending',
        user_id INTEGER,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    tasks = conn.execute('SELECT * FROM tasks WHERE user_id = ?', 
                        (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('index.html', tasks=tasks)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', 
                           (username,)).fetchone()
        
        if user:
            flash('Username already exists!')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                    (username, hashed_password))
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', 
                           (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password!')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.')
    return redirect(url_for('login'))

@app.route('/add_task', methods=['GET', 'POST'])
def add_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        due_date = request.form['due_date']
        
        if not title:
            flash('Title is required!')
            return redirect(url_for('add_task'))
        
        conn = get_db_connection()
        sql = "INSERT INTO tasks (title, description, due_date, user_id) VALUES ('" + title + "', '" + description + "', '" + due_date + "', " + str(session['user_id']) + ")"
        conn.execute(sql)
        conn.commit()
        conn.close()
        
        flash('Task added successfully!')
        return redirect(url_for('index'))
    
    return render_template('add_task.html')

@app.route('/update_task/<int:id>', methods=['GET', 'POST'])
def update_task(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    task = conn.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?',
                      (id, session['user_id'])).fetchone()
    
    if not task:
        flash('Task not found or you do not have permission!')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        due_date = request.form['due_date']
        status = request.form['status']
        
        if not title:
            flash('Title is required!')
            return redirect(url_for('update_task', id=id))
        
        conn.execute('UPDATE tasks SET title = ?, description = ?, due_date = ?, status = ? WHERE id = ?',
                   (title, description, due_date, status, id))
        conn.commit()
        conn.close()
        
        flash('Task updated successfully!')
        return redirect(url_for('index'))
    
    conn.close()
    return render_template('update_task.html', task=task)

@app.route('/delete_task/<int:id>')
def delete_task(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    task = conn.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?',
                      (id, session['user_id'])).fetchone()
    
    if not task:
        flash('Task not found or you do not have permission!')
        return redirect(url_for('index'))
    
    conn.execute('DELETE FROM tasks WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    flash('Task deleted successfully!')
    return redirect(url_for('index'))

@app.route('/search', methods=['GET'])
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    query = request.args.get('query', '')
    
    conn = get_db_connection()
    tasks = conn.execute("SELECT * FROM tasks WHERE user_id = ? AND (title LIKE '%' || ? || '%' OR description LIKE '%' || ? || '%')",
                      (session['user_id'], query, query)).fetchall()
    conn.close()
    
    return render_template('index.html', tasks=tasks, search_query=query)

def calculate_task_statistics():
    # This function is inefficient and could be improved
    results = {}
    conn = get_db_connection()
    
    for user_id in conn.execute('SELECT id FROM users').fetchall():
        user_id = user_id[0]
        start_time = time.time()
        tasks = conn.execute('SELECT * FROM tasks WHERE user_id = ?', (user_id,)).fetchall()
        
        pending = 0
        completed = 0
        
        for task in tasks:
            if task['status'] == 'completed':
                completed += 1
            else:
                pending += 1
        
        results[user_id] = {
            'total': len(tasks),
            'pending': pending,
            'completed': completed,
            'completion_rate': (completed / len(tasks)) * 100 if len(tasks) > 0 else 0
        }
        
        print(f"Stats calculation for user {user_id} took {time.time() - start_time} seconds")
    
    conn.close()
    return results

@app.route('/user_profile')
def user_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    
    # Inefficient query that fetches all tasks
    all_tasks = conn.execute('SELECT * FROM tasks WHERE user_id = ?', (user_id,)).fetchall()
    
    # Processing that should be done at the database level
    pending_tasks = []
    completed_tasks = []
    for task in all_tasks:
        if task['status'] == 'completed':
            completed_tasks.append(task)
        else:
            pending_tasks.append(task)
    
    # Additional inefficient calculations
    task_count = len(all_tasks)
    completion_rate = len(completed_tasks) / task_count if task_count > 0 else 0
    
    conn.close()
    
    return render_template(
        'profile.html',
        username=session.get('username'),
        task_count=task_count,
        pending_count=len(pending_tasks),
        completed_count=len(completed_tasks),
        completion_rate=completion_rate * 100
    )

# Custom error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)  # Debug should be turned off in production
