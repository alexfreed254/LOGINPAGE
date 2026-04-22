from flask import Flask, render_template, request, redirect, session, flash
from supabase import create_client
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret-key")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ─────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────
@app.route('/')
def home():
    return redirect('/login')


# ─────────────────────────────────────────────
# REGISTER
# ─────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']
        name     = request.form.get('full_name', '')

        try:
            res = supabase.auth.sign_up({
                "email": email,
                "password": password
            })

            if res.user:
                # Update profile with full name
                supabase.table('profiles').update({
                    "full_name": name
                }).eq('id', res.user.id).execute()

                flash('Registration successful! Please log in.', 'success')
                return redirect('/login')
            else:
                flash('Registration failed. Try again.', 'error')

        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

    return render_template('register.html')


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']

        try:
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if res.user:
                session['user']       = email
                session['user_id']    = res.user.id
                session['user_token'] = res.session.access_token
                flash('Logged in successfully!', 'success')
                return redirect('/dashboard')
            else:
                flash('Invalid email or password.', 'error')

        except Exception as e:
            flash(f'Login failed: {str(e)}', 'error')

    return render_template('login.html')


# ─────────────────────────────────────────────
# DASHBOARD — shows user profile + posts
# ─────────────────────────────────────────────
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    try:
        # Fetch profile from DB
        profile_res = supabase.table('profiles') \
            .select('*') \
            .eq('id', session['user_id']) \
            .single() \
            .execute()

        profile = profile_res.data

        # Fetch user's posts from DB
        posts_res = supabase.table('posts') \
            .select('*') \
            .eq('user_id', session['user_id']) \
            .order('created_at', desc=True) \
            .execute()

        posts = posts_res.data

    except Exception as e:
        flash(f'Error loading data: {str(e)}', 'error')
        profile = {}
        posts   = []

    return render_template('dashboard.html',
                           user=session['user'],
                           profile=profile,
                           posts=posts)


# ─────────────────────────────────────────────
# CREATE POST
# ─────────────────────────────────────────────
@app.route('/post/create', methods=['GET', 'POST'])
def create_post():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        title   = request.form['title']
        content = request.form['content']

        try:
            supabase.table('posts').insert({
                "user_id": session['user_id'],
                "title":   title,
                "content": content
            }).execute()

            flash('Post created!', 'success')
            return redirect('/dashboard')

        except Exception as e:
            flash(f'Error creating post: {str(e)}', 'error')

    return render_template('create_post.html')


# ─────────────────────────────────────────────
# EDIT POST
# ─────────────────────────────────────────────
@app.route('/post/edit/<post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        title   = request.form['title']
        content = request.form['content']

        try:
            supabase.table('posts').update({
                "title":   title,
                "content": content
            }).eq('id', post_id).eq('user_id', session['user_id']).execute()

            flash('Post updated!', 'success')
            return redirect('/dashboard')

        except Exception as e:
            flash(f'Error updating post: {str(e)}', 'error')

    # Load existing post
    try:
        post_res = supabase.table('posts') \
            .select('*') \
            .eq('id', post_id) \
            .eq('user_id', session['user_id']) \
            .single() \
            .execute()
        post = post_res.data
    except Exception as e:
        flash(f'Post not found: {str(e)}', 'error')
        return redirect('/dashboard')

    return render_template('edit_post.html', post=post)


# ─────────────────────────────────────────────
# DELETE POST
# ─────────────────────────────────────────────
@app.route('/post/delete/<post_id>', methods=['POST'])
def delete_post(post_id):
    if 'user' not in session:
        return redirect('/login')

    try:
        supabase.table('posts') \
            .delete() \
            .eq('id', post_id) \
            .eq('user_id', session['user_id']) \
            .execute()

        flash('Post deleted.', 'success')

    except Exception as e:
        flash(f'Error deleting post: {str(e)}', 'error')

    return redirect('/dashboard')


# ─────────────────────────────────────────────
# UPDATE PROFILE
# ─────────────────────────────────────────────
@app.route('/profile/update', methods=['POST'])
def update_profile():
    if 'user' not in session:
        return redirect('/login')

    full_name  = request.form.get('full_name', '')
    avatar_url = request.form.get('avatar_url', '')

    try:
        supabase.table('profiles').update({
            "full_name":  full_name,
            "avatar_url": avatar_url
        }).eq('id', session['user_id']).execute()

        flash('Profile updated!', 'success')

    except Exception as e:
        flash(f'Error updating profile: {str(e)}', 'error')

    return redirect('/dashboard')


# ─────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'success')
    return redirect('/login')


if __name__ == '__main__':
    app.run(debug=True)
