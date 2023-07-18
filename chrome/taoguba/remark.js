// 显示收藏内容面

function createItemUI(info) {

}

function loadUI() {
    let WIDTH = 300;
    let x = $(document).width() - WIDTH;
    let cnt = $('<div style="width: ' + WIDTH + 'px; height: 100%; left: ' + x + 'px; top: 50px; position:fixed; z-index: 999999; background-color: #ccc; " > </div>');
    $(document.body).append(cnt);

    $.get('http://localhost:8071/query_taoguba_remark', function(rs) {
        console.log(rs);
        //let u = createItemUI(rs[i]);
        //cnt.append(u);
    });
}

loadUI();