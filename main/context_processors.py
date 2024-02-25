from .forms import ProductSearchForm

def common_context(request):
    search_form = ProductSearchForm(request.GET) #検索フォームから取得
    genre = request.GET.get("genre")#URLからジャンルを取得
    if genre:#ジャンルから絞り込みがされたとき
        search_form = ProductSearchForm({"keyword":genre}) #フォームにジャンル名を入れ込む
    context = {
        "search_form": search_form,
    }
    return context