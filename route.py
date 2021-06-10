import pymysql
from pymysql.cursors import DictCursor
from flask import render_template, redirect, url_for, request, session, flash, send_file
from passlib.hash import pbkdf2_sha512 as phash
import os
import shutil
import xlsxwriter as xlsx
from werkzeug.utils import secure_filename
from datetime import datetime, date
from app import app

dbname = 'apteka'
dbuser = 'kansho'
dbpassword = 'lde9aP2f4RPsSPEC'
dbhost = '94.103.92.208'

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_STATIC = os.path.join(APP_ROOT, 'static')
UPLOAD_FOLDER = os.path.join(APP_STATIC, 'img')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXT = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


@app.route('/')
def index():
    if 'user' in session:
        return render_template('index.html', usr=session['user'])
    else:
        return render_template('index.html', usr=None)


@app.route('/catalog')
def catalog():
    conn = pymysql.connect(
        host=dbhost,
        user=dbuser,
        password=dbpassword,
        db='apteka',
        charset='utf8',
        cursorclass=DictCursor
    )
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM goods ORDER BY id;')
    goods = cursor.fetchall()
    conn.close()

    if 'user' in session:
        return render_template('catalog.html', goodsAll=goods, goodsShown=goods, usr=session['user'])
    else:
        return render_template('catalog.html', goodsAll=goods, goodsShown=goods, usr=None)


@app.route('/catalog', methods=['POST'])
def catalog_search():
    conn = pymysql.connect(
        host=dbhost,
        user=dbuser,
        password=dbpassword,
        db='apteka',
        charset='utf8',
        cursorclass=DictCursor
    )
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM goods ORDER BY id;')
    goods = cursor.fetchall()
    conn.close()
    name = request.form.get('searchQuery')
    print(type(name), name)
    if name == '':
        if 'user' in session:
            return render_template('catalog.html', goodsAll=goods, goodsShown=goods, usr=session['user'])
        else:
            return render_template('catalog.html', goodsAll=goods, goodsShown=goods, usr=None)
    else:
        conn = pymysql.connect(
            host=dbhost,
            user=dbuser,
            password=dbpassword,
            db='apteka',
            charset='utf8',
            cursorclass=DictCursor
        )
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM goods WHERE name = %s', (name,))

        rr = cursor.fetchall()

        conn.close()
        if 'user' in session:
            return render_template('catalog.html', goodsAll=goods, goodsShown=rr, usr=session['user'])
        else:
            return render_template('catalog.html', goodsAll=goods, goodsShown=rr, usr=None)


@app.route('/login')
def login():
    if 'user' in session:
        flash('Ошибка: вы уже вошли', category='error')
        return redirect(url_for('index'))
    return render_template('login.html', usr=None)


@app.route('/login', methods=['POST'])
def login_post():
    log = request.form.get('login')
    pas = request.form.get('password')

    conn = pymysql.connect(
        host=dbhost,
        user=dbuser,
        password=dbpassword,
        db='apteka',
        charset='utf8',
        cursorclass=DictCursor
    )
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM admins WHERE login = %s', (log,))
    rr = cursor.fetchone()

    conn.close()

    if rr is not None:
        if phash.verify(pas, rr['password']):
            flash('Успешный вход', category='message')
            session['user'] = rr['id']
            os.mkdir(APP_ROOT + '/temp')
            return redirect(url_for('index'))
        else:
            flash("Ошибка входа", category='error')
            return redirect(url_for('login'))
    else:
        flash("Ошибка входа", category='error')
        return redirect(url_for('login'))


@app.route('/profile')
def profile():
    if 'user' not in session:
        flash('Ошибка', category='error')
        return redirect(url_for('index'))
    else:
        conn = pymysql.connect(
            host=dbhost,
            user=dbuser,
            password=dbpassword,
            db='apteka',
            charset='utf8',
            cursorclass=DictCursor
        )
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM goods ORDER BY id ')
        goods = cursor.fetchall()
        conn.close()
        return render_template('profile.html', goods=goods, date=date.today())


@app.route('/profileadd', methods=['POST'])
def prodadd():
    file = request.files['file']
    if allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(app.config['UPLOAD_FOLDER'] + '/' + filename)
        conn = pymysql.connect(
            host=dbhost,
            user=dbuser,
            password=dbpassword,
            db='apteka',
            charset='utf8',
            cursorclass=DictCursor
        )
        cursor = conn.cursor()
        pName = request.form.get('name')
        pPrice = request.form.get('price')
        pAmount = request.form.get('amount')
        cursor.execute("INSERT INTO goods (id, name, price, amount, img) VALUES (DEFAULT, %s, %s, %s, %s)",
                       (pName, pPrice, pAmount, 'img/' + filename))
        conn.commit()
        flash('Продукт успешно добавлен', category='message')
    return redirect(url_for('profile'))


@app.route('/profilechange', methods=['POST'])
def prodchange():
    changeid = request.form.get('goodid')
    conn = pymysql.connect(
        host=dbhost,
        user=dbuser,
        password=dbpassword,
        db='apteka',
        charset='utf8',
        cursorclass=DictCursor
    )
    cursor = conn.cursor()
    amt = int(request.form.get('prodAmount'))
    prevamt = int(request.form.get('prodAmountValue'))
    prc = request.form.get('prodPrice')
    act = request.form.get('submit')
    if act == 'Удалить':
        cursor.execute('DELETE FROM goods WHERE id = %s', (changeid,))
        flash('Продукт успешно удален', category='message')
    elif amt != prevamt or prc != request.form.get('prodPriceValue'):
        cursor.execute('UPDATE goods SET amount = %s, price = %s WHERE id = %s', (amt, prc, changeid,))
        if amt != prevamt:
            print(request.form.get('prodRowNameValue'), prevamt, amt - prevamt, date.today())
            cursor.execute('INSERT INTO changes (id, name, `before`, `change`, date) VALUES (NULL, %s, %s, %s, %s)',
                           (request.form.get('prodRowNameValue'), prevamt, amt - prevamt, date.today()))
        flash('Продукт успешно изменен', category='message')
    else:
        flash('Ничего не произошло :(', category='message')

    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('profile'))


def make_excel(rr):
    infos = []
    try:
        change_info = {'name': rr[0]['name'], 'before': rr[0]['before'], 'after': rr[0]['before']}
    except IndexError:
        flash('Ошибка: отсутствуют изменения', category='error')
        return redirect(url_for('profile'))
    for i in rr:
        try:
            if rr[rr.index(i) + 1]['name'] != i['name']:
                change_info['after'] += i['change']
                a = change_info.copy()
                infos.append(a)
                change_info['name'] = rr[rr.index(i) + 1]['name']
                change_info['before'] = rr[rr.index(i) + 1]['before']
                change_info['after'] = rr[rr.index(i) + 1]['before']
            else:
                change_info['after'] += i['change']
        except:
            change_info['after'] += i['change']
            infos.append(change_info)
    print(infos)
    name = os.path.join(APP_ROOT, 'temp', datetime.now().strftime('%Y%m%d-%H%M%S') + '.xlsx')
    wbook = xlsx.Workbook(name)
    wsheet = wbook.add_worksheet()
    wrow = 1
    wcol = 0
    wsheet.write(0, 0, "Название")
    wsheet.write(0, 1, "Кол-во в начале")
    wsheet.write(0, 2, "Кол-во в конце")
    for i in infos:
        wsheet.write(wrow, 0, i['name'])
        wsheet.write(wrow, 1, i['before'])
        wsheet.write(wrow, 2, i['after'])
        wrow += 1
    wbook.close()
    print(name)
    return send_file(name, as_attachment=True)


@app.route('/profileGetAccounting', methods=['POST'])
def prodGetAcc():
    print(request.form)
    d1 = request.form.get('AccDate1')
    d2 = request.form.get('AccDate2')
    conn = pymysql.connect(
        host=dbhost,
        user=dbuser,
        password=dbpassword,
        db='apteka',
        charset='utf8',
        cursorclass=DictCursor
    )
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM changes WHERE (date BETWEEN %s AND %s )ORDER BY id ASC", (d1, d2))
    rr = cursor.fetchall()
    conn.close()
    return make_excel(rr)


@app.route('/logout')
def logout():
    shutil.rmtree(os.path.join(APP_ROOT, 'temp'), ignore_errors=True)
    session.pop('user', None)
    return redirect(url_for('index'))


@app.errorhandler(404)
@app.errorhandler(405)
def page_not_found(e):
    return render_template('404.html', usr=None), 404


