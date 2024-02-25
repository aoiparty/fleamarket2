function sendRequest(){
    const xhr = new XMLHttpRequest();
    const tabList = document.querySelectorAll(".tab");
    tabList.forEach(function (element, index){
        element.addEventListener("click", function(ev){
            const preActiveTab = document.querySelector(".active");
            preActiveTab.classList.remove("active");
            const activeTab = element;
            activeTab.classList.add("active");
        });
    });
}
sendRequest();