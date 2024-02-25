from distutils.log import Log
from shutil import register_unpack_format
from typing import Any
from django.db.models.query import QuerySet
# from socket import fromshare
from django.shortcuts import render

from django.views.generic import TemplateView

from django.contrib.auth.mixins import LoginRequiredMixin 
from django.views.generic import ListView,DetailView,FormView,TemplateView,DeleteView,UpdateView
from .models import Genre,Product,Address,ProductImage,Like
from django.db.models import Count, Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy
from django.http import Http404

# ...
from django.contrib.auth.decorators import login_required
# ...
from django.conf import settings
from .forms import (
    CustomProductImageFormSet,
    #OnSaleProductForm,
    PaymentForm,
    ProductSearchForm,
    ProductSellForm,
    AddressForm,
    AccountUpdateForm,
)
from .models import Genre, Product, Like, ProductImage,Address, Payment, Order,Notification

import stripe
#決済処理サービス

from django.contrib.auth import get_user_model
# ...

from django.urls import reverse_lazy,reverse
#reverse 転移先

# Create your views here.

class HomeView(TemplateView):
    template_name = "main/home.html"

class HomeView(LoginRequiredMixin,ListView):
    template_name = "home.html"
    model = Product
    context_object_name = "items"

    def get_queryset(self):
        queryset=super().get_queryset()
        #ListViewによって一覧化したデフォルトのデータをすべて取得
        #さらに情報を追加↓
        queryset = (
            queryset.exclude(exhibitor=self.request.user)
            #ログイン者の投稿した商品以外
            .filter(sales_status="on_display")
            #条件：出品中であるもの
            .prefetch_related("product_images")
            #クエリ最適化と逆参照（prefetch_related）
            .order_by("-uploaded_at")[:6]
            #投稿日時順（最新）に、頭から六つの手前まで
        )
        return queryset #htmlで”items”として使われる
        #queryset = モデルクラス.objects.メソッド(引数)
        
    def get_context_data(self, **kwargs):
        #テンプレートへ情報を渡す関数
        #クエリセットはProductで使用したから使えない
        #複数のモデルを一覧表示する時、一つはクエリセット、もう一つはgetcontextdataを使う
        #クエリセットの方が複雑にデータを取得
        context = super().get_context_data(**kwargs)
        context["genres"] = Genre.objects.all()
        return context

class ProductListView(LoginRequiredMixin,ListView):
    template_name = "product_list.html"
    model = Product
    context_object_name = "items"
    def get_queryset(self):
        queryset = super().get_queryset
        queryset = ( 
            queryset.prefetch_related("product_images").order_by("-uploaded_at")
        )
        genre = self.request.GET.get("genre")
        if genre:
            queryset = queryset.filter(genre__name=genre)

        search_form = ProductSearchForm(self.request.GET)
        if search_form.is_valid():#適切に打たれていたら
            keyword = search_form.cleaned_data["keyword"]#キーワードを検索
            if keyword:
                keywords = keyword.split()# split()メソッド...空白文字でワードを区切る　ex.「バイク　川崎　ミラー」
                for k in keywords:#[バイク,川崎,ミラー]
                    queryset = queryset.filter(name__icontains=k)
        return queryset




#[商品詳細画面]　DetailView
class ProductDetailView(LoginRequiredMixin,DetailView):
    template_name = "product_detail.html"
    model = Product
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.select_related("exhibitor", "genre").annotate(
            likes_count=Count("likes_received"),
            is_liked=Exists(
                Like.objects.filter(user=self.request.user, product=OuterRef("pk"))
            ),
        )
        return queryset

#いいね
@require_POST
def product_like(request, pk):
    product = get_object_or_404(Product, pk=pk)
    Like.objects.create(user=request.user, product=product)
    return redirect("main:product_detail", pk)

#いいねの取り消し
@require_POST
def product_unlike(request, pk):
    product = get_object_or_404(Product, pk=pk)
    Like.objects.filter(user=request.user, product=product).delete()
    return redirect("main:product_detail", pk)




@login_required
def product_sell(request):
    if request.method == "GET":
        product_image_formset = CustomProductImageFormSet(
            queryset=ProductImage.objects.none()
        )
        product_sell_form = ProductSellForm()
    elif request.method == "POST":
        product_image_formset = CustomProductImageFormSet(
            request.POST,
            request.FILES,
        )
        product_sell_form = ProductSellForm(request.POST)
        if product_image_formset.is_valid() and product_sell_form.is_valid():
            new_product = product_sell_form.save(commit=False)
            new_product.exhibitor = request.user
            new_product.sales_status = "on_display"
            new_product.save()
            new_product_images = product_image_formset.save(commit=False)
            for new_product_image in new_product_images:
                if new_product_image.image:
                    new_product_image.product = new_product
                    new_product_image.save()
            return redirect("main:home")
    context = {
        "image_form": product_image_formset,
        "text_form": product_sell_form,
    }
    return render(request, "main/product_sell.html", context)


#
#商品購入手続き
#
#session #dispatch #get_context_data

# 1

#　商品IDと購入価格・使用ポイント（formから）を取得し保存（セッション）する
class PurchaseConfirmationView(LoginRequiredMixin, FormView):
    template_name = "main/purchase_confirmation.html"
    form_class = PaymentForm
    success_url = reverse_lazy("main:address")

    #存在することを確認
    def dispatch(self, request, *args, **kwargs):
        self.item = get_object_or_404(
            Product.objects.prefetch_related("product_images"), pk=self.kwargs["pk"]
        )
        return super().dispatch(request, *args, **kwargs)
    #取得
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["item"] = self.item
        return context
    #保存
    def form_valid(self, form):
        self.request.session["item_pk_info"] = self.kwargs["pk"]
        self.request.session["purchase_info"] = form.cleaned_data
        return super().form_valid(form)

    #formからprice情報を取得
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["price"] = self.item.value
        return kwargs


# 2

#受け取り住所の入力
class InputAddressView(LoginRequiredMixin, FormView):
    template_name = "main/input_address.html"
    form_class = AddressForm
    success_url = reverse_lazy("main:payment")

#前画面でちゃんと情報があるか確認（なかったらHomeへ）
    def dispatch(self, request, *args, **kwargs):
        if "purchase_info" not in request.session or "item_pk_info" not in request.session:
            return redirect("main:home")
        return super().dispatch(request, *args, **kwargs)
#次画面に行く前に確認
    def form_valid(self, form):
        self.request.session["address_info"] = form.cleaned_data
        return super().form_valid(form)


# 3

#支払い方法
class InputPaymentView(LoginRequiredMixin, TemplateView):
    template_name = "main/input_payment.html"

    def dispatch(self,request,*args,**kwargs):
        if "address_info" not in request.session:
            return redirect("main:home")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item_pk = self.request.session["item_pk_info"]
        #商品情報を取得
        item = get_object_or_404(
            Product.objects.prefetch_related("product/_images")
        )
        #商品画像を取得
        context["item"] = item

        #　↑ページの先頭に購入する商品を表示するため

        #　Stripeを使用するために鍵（公開キー）（APIキー）を引き出す
        context["STRIPE_PUBLISHABLE_KEY"] = settings.STRIPE_PUBLISHABLE_KEY
        return context


     #Stripeサーバーで作成された、カード情報のトークン（暗号）を
     # セッションに入れる　→　（Stripe本会員であることの証明）
    def post(self,request,*args,**kwargs):
        if "stripeToken" not in self.request.POST:
            #stripeToken
            return render(request,"main/input_payment.html",{"message":"正しく処理されませんでした。もう一度入力してください。"},)
        else:
            self.request.session["card_info"] = request.POST["stripeToken"]
            return redirect("main:final_confirmation")


# 4

#注文の確認
class CreateCheckoutView(LoginRequiredMixin, TemplateView):
    template_name = "main/final_confirmation.html"

    def dispatch (self,request,*args,**kwargs):
        #前ページのセッションの確認
        if "card_info" not in  request.session:
            return redirect("main:home")

        #今までセッションで保存してきた情報を取得してクラス内変数に（最初にしたいからdispatch関数に）
        self.item_pk = self.request.session["item_pk_info"]
        self.purchase_info = self.request.session["purchase_info"]
        self.address_info = self.request.session["address_info"]
        self.stripe_token = self.request.session["card_info"]
        #親クラスから引き継ぐ
        return super().dispatch(request, *args, **kwargs)

    #HtMLに表示する情報をデータベースから取得
    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)
        #上の情報を取得

        item = get_object_or_404(
            Product.objects.prefetch_related("product/_images"), pk=self.item_pk
        )
        #写真を逆参照することによって取得
        context["item"]=item
        context["purchase"]=self.purchase_info
        context["address"] = self.address_info
        return context

    #決済処理の実装
    def post(self, request, *args, **kwargs):
        #StripeのAPIをsettingsから入れる
        #（二つの情報のやりとりの窓口の鍵）
        stripe.api_key = settings.STRIPE_API_KEY
        price = self.purchase_info["total_amount"]
        try:
            charge = stripe.Charge.create(
                amount=int(price),
                currency="jpy",
                source=self.stripe_token, #暗号化
                description="FreeMa",
            )
            #不正アクセス、正しくないAPIキーの時
        except stripe.error.CardError:
            return render(
                request,
                "main/error.html",
                {"message": "決済に失敗しました。"},
            )

        # データベースの保存
        
        
         
        
        

        # Aderess
        address = Address.objects.create(
            first_name=self.address_info["first_name"],
            last_name=self.address_info["last_name"],
            first_name_kana=self.address_info["first_name_kana"],
            last_name_kana=self.address_info["last_name_kana"],
            postal_code=self.address_info["postal_code"],
            prefecture=self.address_info["prefecture"],
            address=self.address_info["address"],
            tel=self.address_info["tel"],
        )

        # Payment　
        payment = Payment.objects.create(
            user=request.user, stripe_charge_id=charge["id"]
            #stripe_charger_id:決済番号（後で決済情報を確認することができる）
        )
        # ...
        product = get_object_or_404(Product, pk=self.item_pk)
        #sessionで保存してきたところから取得

        #購入情報の作成
        order = Order.objects.create(
            product=product,
            price=price,
            purchaser=request.user,
            delivery_status="before_shipping",
            #配達中or配達済みor未配達
            address=address,
            payment=payment,
        )
        # ...
        # ...
        product.sales_status = "sold"
        #出品状態を「売り切れ」にして
        product.save()
        # データベースに保存

        
        request.user.point -= int(self.request.session["purchase_info"]["point"])
        #所有ポイントから今回の使用ポイントが引かれて

        request.user.save()
        # 保存

        #出品者は売れた分のポイントがもらえる
        exhibitor = product.exhibitor
        point = product.value - int(product.value * 0.1)
        #売れた金額の９割ぶんのポイントを出品者に追加して
        exhibitor.point += point
        exhibitor.save()
        # 保存
        # 出品者に対する通知の生成
        Notification.objects.create(user=exhibitor, order=order, is_action=True)

@require_POST
def change_delivery_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if order.delivery_status == "before_shipping":
        order.delivery_status = "shipped"
        order.save()
        # 購入者に対する通知の作成
        purchaser = order.purchaser
        Notification.objects.create(user=purchaser, order=order, is_action=False)
    elif order.delivery_status == "shipped":
        return redirect("main:product_detail", order.product.pk)

@require_POST
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk, exhibitor=request.user)
    product.delete()
    return redirect("main:home")

#アカウント画面

#アカウント情報を取得
User = get_user_model()

class AccountView(LoginRequiredMixin,DetailView):
    template_name = "main/account.html"
    model = User
#get_object関数で取得すれば、id(pk)を使う必要がない
    def get_object(self):
        return self.request.user

#　利用規約・プライバシーポリシー
# ...
class TermsView(TemplateView):
    template_name = "main/terms.html"

class PrivacyPolicyView(TemplateView):
    template_name = "main/privacy_policy.html"

#アカウント削除
class AccountDeleteView(LoginRequiredMixin, DeleteView):
    template_name = "main/account_delete.html"
    model = User
    success_url = reverse_lazy("main:account_delete_done")

    def get_object(self):
        return self.request.user

class AccountDeleteDoneView(TemplateView):
    template_name = "main/account_delete_done.html"



class AccountDetailView(LoginRequiredMixin,DetailView):
    template_name = "main/account_detail.html"
    model = User

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.prefetch_related("products_exhibited__product_images").annotate(products_count=Count("products_exhibited"))

        return queryset
        ##prefetch_related：逆参照.
        #__は.のような役割
        #prefetch_related(A__B)でqueryset → A → B へ逆参照できる　
        # annonate order_byでは処理しきれないような複雑な順番選びをするときに使う（情報の追加）
        #Count()で数をとってくる

        
class ProductLikedListView(LoginRequiredMixin,ListView):
    template_name = "main/product_liked_list.html"
    model = Product
    context_object_name = "liked_products"
    def get_queryset(self):
        queryset = super().get_queryset
        queryset = queryset.filter(
            likes_received__user=self.request.user
        ).prefetch_related("product_images")
        return queryset
    
class ProductPurchasedListView(LoginRequiredMixin,ListView):
    template_name = "main/product_purchased_list.html"
    model = Product
    context_object_name = "purchased_products"
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = (
            queryset.filter(orders_received__purchaser=self.request.user)
            #orders_received:Product モデル → Order モデルで逆参照するための related_name
            .prefetch_related("product_images")
            .order_by("-uploaded_at")
        )
        #...
        if "delivery_status" in self.request.GET:
            delivery_status=self.request.GET["delivery_status"]
            if delivery_status == "before_shipping":
                queryset = queryset.filter(
                    orders_received__delivery_status="before_shipping"
                )
            elif delivery_status == "other":
                queryset = queryset.exclude(
                    orders_received__delivery_status="before_shipping"
                )
            else:
                raise Http404
        else:
            queryset = queryset.filter(
                orders_received__delivery_status="before_shipping"
                )
        
        return queryset
    
    
class ProductExibitListView(LoginRequiredMixin,ListView):
    def get_queryset(self):
        if "salesStatus" in self.request.GET:
            sales_status = self.request.GET["salesStatus"]
            if sales_status:
                if sales_status == "all":
                    queryset = queryset
                elif sales_status == "on_display":
                    queryset = queryset.filter(sales_status="on_display")
                elif sales_status == "sold":
                    queryset = queryset.filter(sales_status="sold")
                else:
                    raise Http404
        return queryset

class AccountUpdateView(LoginRequiredMixin,UpdateView):
    model = User
    form_class = AccountUpdateForm
    template_name = "main/account_update.html"

    def get_success_url(self):#転移先のページを定義
        return reverse("main:account_detail",kwargs={"pk":self.request.user.pk})
        #kwargs 辞書型引数
    def get_object(self):
        return self.request.user
    
#通知機能
class NotificationView(LoginRequiredMixin,ListView):
    model = Notification
    template_name="main/notification.html"
    context_object_name = "notifications"

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = (
            queryset.filter(user=self.request.user,is_action=True)# is_actionアクションかお知らせかの区別用
            .select_related("order__product") #順方向
            .prefetch_related("order__product__product_iamges") #逆方向
            .order_by("-created_at")
        )
        return queryset

    
