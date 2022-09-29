from contextlib import redirect_stderr
from hashlib import sha256
from turtle import title
from unicodedata import name
from unittest import result
from webbrowser import get
from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
import email_validator
from functools import wraps

#kullanıcı giriş decorator'ı
def login_required(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        if "loggin_in" in session:
            return f(*args,**kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapınız","danger")
            return redirect(url_for("login"))
    return decorated_function


#kullanıcı kayıt formu

class RegistrationForm(Form):
    name=StringField("İsim Soyisim",validators=[validators.Length(min=4,max=25)])
    username=StringField("Kullanıcı adı",validators=[validators.Length(min=5,max=25)])
    email=StringField("Email",validators=[validators.Email(message="lütfen geçerli bir email adresi giriniz..")])
    password=PasswordField("Parola",validators=[validators.Length(min=4,max=25),validators.DataRequired(message="Lütfen bir parola belirleyiniz"), validators.EqualTo(fieldname="confirm",message="Parolanız uyuşmuyor") ])
    
    confirm=PasswordField("Parola Doğrula")

class LoginForm(Form):
    username=StringField("Kullanıcı adı")
    password=PasswordField("Parola")

    

app = Flask(__name__)
app.secret_key="myblog"

app.config["MYSQL_HOST"]="localhost"
app.config["MYSQL_USER"]="root"
app.config["MYSQL_PASSWORD"]=""
app.config["MYSQL_DB"]="ybblog"
app.config["MYSQL_CURSORCLASS"]="DictCursor"

mysql=MySQL(app)


    
@app.route("/")

def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")

#Arama URL
@app.route("/search",methods=["GET","POST"])
def search():
    if request.method=="GET":
        return redirect(url_for("index"))
    else:
        keyword=request.form.get("keyword")
        cursor=mysql.connection.cursor()
        
        sorgu="select * from articles where title like '%"+ keyword+ "%'"
        result=cursor.execute(sorgu)
        
        if result ==0:
            flash("Aranan kelimeye uygun makale bulunamadı...","warning")
            return redirect(url_for("articles"))
        else:
            articles=cursor.fetchall();
            return render_template("articles.html",articles=articles)
        
    


@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor=mysql.connection.cursor()
    sorgu="select * from articles where author =%s and id=%s"
    
    result=cursor.execute(sorgu,(session["username"],id))
    
    if result>0:
        sorgu2="DELETE FROM articles WHERE id=%s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya bu makaleyi silemeye yetkiniz bulunmamaktadır","danger")
        return redirect(url_for("index"))
    
    
    return render_template("deletearticle.html")
#Makale güncelleme

@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required
def update(id):

    if request.method=="GET":
        cursor=mysql.connection.cursor()
        sorgu="select * from articles where author =%s and id=%s"
        
        result=cursor.execute(sorgu,(session["username"],id))
        if result>0:
            article=cursor.fetchone()
            form=ArticleForm()
            form.title.data=article["title"]
            form.content.data=article["content"]
            return render_template("update.html",form=form)
    
        else:
            flash("Böyle bir makale yok veya bu makaleyi güncellemeye yetkiniz bulunmamaktadır","danger")
            return redirect(url_for("index"))
    else:
        form=ArticleForm(request.form)
        
        newTitle=form.title.data
        newContent=form.content.data
        
        sorgu2="Update articles Set title=%s,content=%s where id=%s"
        
        cursor=mysql.connection.cursor()
        
        cursor.execute(sorgu2,(newTitle,newContent,id))
        mysql.connection.commit()
        flash("Makale başarıyla güncellendi","success")
        return redirect(url_for("dashboard"))
        
 

@app.route("/articles")
def articles():
    cursor=mysql.connection.cursor()
    
    sorgu="select * from articles"
    
    result=cursor.execute(sorgu)
    
    if result>0:
        articles=cursor.fetchall()
        return render_template("articles.html",articles=articles)
    else:
        return render_template("articles.html")
    



@app.route("/register",methods=["GET","POST"])
def register():
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate() :
        
        name=form.name.data
        email=form.email.data
        password=sha256_crypt.encrypt(form.password.data)
        username=form.username.data
        
        cursor=mysql.connection.cursor()
        
        sorgu="INSERT INTO  users(name,email,username,password) VALUES(%s,%s,%s,%s)"
        
        cursor.execute(sorgu,(name,email,username,password))
        
        mysql.connection.commit()
        
        cursor.close()
        
        flash("Başarıyla Kayıt Oldunuz...","success")
        
        return redirect(url_for("login"))
    else:
        return render_template("register.html",form=form)
    
@app.route("/login",methods=["GET","POST"])
def login():
    
    form=LoginForm(request.form)
    
    if request.method=="POST":
        password=form.password.data
        username=form.username.data
        
        cursor=mysql.connection.cursor()
        
        sorgu="select * from users where username= %s"
        
        result=cursor.execute(sorgu,(username,))
        
        if result>0:
            data=cursor.fetchone()

            
            real_password=data["password"]
            if sha256_crypt.verify(password,real_password):
                flash("Giriş Başarılı","success")
                
                session["loggin_in"]=True
                session["username"]=username
                session["name"]=data["name"]
                
                
                return redirect(url_for("index"))
                
            else:
                flash("Parolanızı yanlış girdiniz...","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunmuyor","danger")
            return redirect(url_for("login"))
    
    
    
    return render_template("login.html",form=form)
    

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

#Detay Sayfası

@app.route("/article/<string:id>")
def article(id):
    cursor=mysql.connection.cursor()
    
    sorgu="Select * from articles where id=%s"
    
    result=cursor.execute(sorgu,(id,))
    
    if result>0:
        article=cursor.fetchone()
        return render_template("article.html",article=article)
    else:
        return render_template("article.html")

@app.route("/dashboard")
@login_required
def dashboard():
    cursor=mysql.connection.cursor()
    sorgu="Select * from articles where author=%s"
    
    result=cursor.execute(sorgu,(session["username"],))
    
    if result>0:
        articles=cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    else:
        return render_template("dashboard.html")
    
    return render_template("dashboard.html")

@app.route("/addarticle",methods=["GET","POST"])
def addarticle():
    form=ArticleForm(request.form)
    if request.method=="POST" and form.validate():
        title=form.title.data
        content=form.content.data
        
        cursor=mysql.connection.cursor()
        
        sorgu="Insert into articles(title,author,content) VALUES (%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        
        cursor.close()
        
        flash("Makale başarıyla eklendi","success")
        
        return redirect(url_for("dashboard"))    
    
    return render_template("addarticle.html",form=form)



#makale form


class ArticleForm(Form):
    title=StringField("Makale Başlığı",validators=[validators.Length(min=5,max=100)])
    content=TextAreaField("Makale içeriği",validators=[validators.Length(min=10)])

if __name__=="__main__":
    app.run(debug=True)
    
