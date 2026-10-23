
/**
*    update 2025.02.28 改善施策
*    update 2026.01.06 Cookie secure対策
*/
// Library
var Library = (function(){


    var _sampleVale  = 10;
    var _DEVICE_PC = 0;
    var _DEVICE_TAB = 1;
    var _DEVICE_SP = 2;
   //2025.02.28
    var _COOKIE_AGREEMENT = 'ownersmanualwebomjpn';


    var _getDateTime = function(){
        return new Date().getTime() ;
    }

    return {

        // sp tablet用
        DIRECTION_TATE : 0,
        DIRECTION_YOKO : 1,
        WIDTH_TAB : 991,
        WIDTH_SP : 479,
        myScale : 1,
        getUA : function()
        {
            var userAgent = window.navigator.userAgent.toLowerCase();
            var appVersion = window.navigator.appVersion.toLowerCase();

            if (userAgent.indexOf('opera') != -1) {
              return 'opera';
            } else if (userAgent.indexOf('msie') != -1) {
                 //IE6～9
                if (appVersion.indexOf("msie 8.") != -1) {
                    return 'IE8';
                }else if (appVersion.indexOf("msie 9.") != -1) {
                    return 'IE9';
                }else{
                    return 'IE';
                }
            } else if (userAgent.indexOf('chrome') != -1) {
              return 'chrome';
            } else if (userAgent.indexOf('safari') != -1) {
              return 'safari';
            } else if (userAgent.indexOf('gecko') != -1) {
              return 'gecko';
            } else {
              return false;
            }
        },

        //PC TABLET共通の目次ナビ
        setNav: function()
        {
            //20160813
            if( typeof MENU != 'undefined' ){
                if (location.pathname.indexOf('/pc/') < 0 && location.pathname.indexOf('/sp/') < 0 && location.pathname.indexOf('/tablet/') < 0 && location.pathname.indexOf('/details/') < 0 && location.pathname.indexOf('/detailsnavi/') < 0) {
                    MENU = MENU.replace(/..\/details/g, 'details');
                    MENU = MENU.replace(/..\/images/g, 'images');
                }
                $('#nav').html('').append(MENU);
            }

            $('#nav div.listTitle').click(function(){
                var myUL = $(this).next('ul');
                var myParent = myUL.closest('li');

                if( myUL.css('display') == "block" ){
                    myParent.removeClass('active');
                    myUL.hide();
                    //最上位メニューをクリックした際、子要素を全て閉じる
                    if(myParent.attr('id') != 'undefined'){
                        myUL.find('ul').hide();
                        myParent.find('li').removeClass('active');
                    }
                }else{
                    myUL.slideDown(300);
                    myParent.addClass('active');
                }
            });
            $('#nav div.listTitle').hover(
                function(){
                    $(this).addClass('hover');
                },
                function(){
                    $(this).removeClass('hover');
                }
            );
        },

        //search絞り込み 2025.02.10
        setSearchFilter: function(){
            const existingInput = document.querySelector('input[name="d"]');
            if (existingInput) {
                existingInput.remove();
            }

            const form = document.querySelector('.mf_finder_searchBox_form');
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'd';
            hiddenInput.value = SEARCH_FILTER_WORD;
            form.appendChild(hiddenInput);
        },

        //ナビの高さを設定
        setNavHeight: function(  ) 
        {
            var my = this;
            //var scrollMax = $('#screen').height() - $('#footer').outerHeight() - window.innerHeight ;
            $('#nav').height( this.getNavHeight() );
            this.setScrollPosition();
        },

        setScrollPosition : function()
        {
            var my = this;
            var scrollMax = $('#screen').height() - $('#footer').outerHeight() - window.innerHeight ;
            var wScroll = $(window).scrollTop();
            var navHeight = this.getNavHeight();
            if( wScroll > scrollMax){
                if( _DEVICE_PC == my.getDeviceFromWidth() ){
                    navHeight = navHeight - (wScroll - scrollMax);
                    $('#nav').height( navHeight );
                }
            }else{
                $('#nav').height( my.getNavHeight() );
            }
        },

        //ナビの高さを取得
        getNavHeight: function(e)
        {
            var winH = window.innerHeight;
            if( this.getUA() == "IE8"){
                 winH = document.documentElement.clientHeight;
            }
            var headerHeight = $('#header').outerHeight();
            var footerHeight = $('#footer').outerHeight();

            navHeight = winH - headerHeight;
            if( _DEVICE_PC == this.getDeviceFromWidth() ){
                navHeight -=  ( parseFloat( $('#container').css('paddingTop') ) - headerHeight + 5 );
            }
            return navHeight;
        },


        //さらに詳しく
        setMore: function (){
            var speed = 200;
            $('dl.more dt').click(function(){
                var my = $(this);
                var dd = $(this).next();
                if( dd.css('display') == "block" ){
                    dd.slideUp( speed ).removeClass( 'active' ) ;
                    my.removeClass( 'active' );
                }else{
                    dd.slideDown( speed ).addClass( 'active' );
                    my.addClass( 'active' );
                }
            })
        },

        //  幅によるデバイス取得。UAによるデバイス取得は getDeviceFromUA()
        getDeviceFromWidth: function()
        {
            var ww = $(window).width();
            var loc = location.pathname;
            var tmp = '';

            if( loc.indexOf('/pc/') > 0 ){
                tmp = _DEVICE_PC;
            }else if( loc.indexOf('/tablet/') > 0){
                tmp = _DEVICE_TAB;
            }else if(loc.indexOf('/sp/') > 0){
                tmp = _DEVICE_SP;
            }else if(loc.indexOf('/details/') > 0 || loc.indexOf('/detailsnavi/') > 0){
                if( ww >= this.WIDTH_TAB ){
                    tmp = _DEVICE_PC;
                }else if( ww < this.WIDTH_TAB && ww > this.WIDTH_SP ){
                    tmp = _DEVICE_TAB;
                }
                else if(  ww <= this.WIDTH_SP ){
                    tmp = _DEVICE_SP;
                }
            }
            return tmp;
        },

        // UAによるデバイス取得 幅によるデバイス取得はgetDeviceFromWidth();
        // 2022.07.19
        getDeviceFromUA: function()
        {
            var ua = navigator.userAgent;
            if(ua.indexOf('LAVIE') >= 0 ){
                var w = $(window).width();
                if( w < this.WIDTH_TAB && w > this.WIDTH_SP ){
                    return _DEVICE_TAB;
                }else{
                    return _DEVICE_SP;
                }
            }
            if(ua.indexOf('iPhone') > 0 || ua.indexOf('iPod') > 0 || ua.indexOf('Android') > 0 && ua.indexOf('Mobile') > 0){
                return _DEVICE_SP;
            }else if(ua.indexOf('iPad') > 0 || ua.indexOf('Android') > 0){
                return _DEVICE_TAB;
            }else{
                return _DEVICE_PC;
            }
        },

        //UAによる切り替え
        setLocation:function()
        {
            var loc = location.pathname;
            var fileName = window.location.href.split('/').pop();
            var rootPath = loc + fileName;

            switch( this.getDeviceFromUA() )
            //switch( _DEVICE_SP )
            {
                case _DEVICE_SP:
                    if( (loc.indexOf('/pc/') > 0 || loc.indexOf('/tablet/') > 0) ){
                        loc = loc.replace( "/pc", "/sp");
                        loc = loc.replace( "/tablet", "/sp");
                        location.href =loc;
                    }
                    if(location.pathname == BASE_DIRECTORY || location.pathname == BASE_DIRECTORY + 'index.html'){
                        location.href = BASE_DIRECTORY + 'sp/';
                    }
                    break;
                case _DEVICE_TAB:

                    if( (loc.indexOf('/pc/') > 0 || loc.indexOf('/sp/') > 0) ){
                        loc = loc.replace( "/pc", "/tablet");
                        loc = loc.replace( "/sp", "/tablet");
                        if( loc.indexOf('list') ){
                            loc = BASE_DIRECTORY + 'tablet/';
                        }
                        location.href =loc;
                    }
                    if( loc == BASE_DIRECTORY || loc == BASE_DIRECTORY + 'index.html'){
                        location.href = BASE_DIRECTORY + 'tablet/';
                    }

                    break;
                case _DEVICE_PC:
                    if( (loc.indexOf('/tablet/') > 0 || loc.indexOf('/sp/') > 0) ){
                        loc = loc.replace( "/tablet", "/pc");
                        loc = loc.replace( "/sp", "/pc");

                        if( loc == BASE_DIRECTORY + 'pc/' ){
                            loc = BASE_DIRECTORY;
                        }
                        if( loc.indexOf('list') ){
                            loc = BASE_DIRECTORY;
                        }
                        location.href =loc;
                    }
                    if( loc == BASE_DIRECTORY + 'pc/index.html' ||  loc == BASE_DIRECTORY + 'index.html' ){
                        loc = BASE_DIRECTORY;
                        location.href = loc;
                    }
                    break;
            }
        },

        //2018.02.05 change
        setSearchNav : function()
        {
            var searchBox = $('#MF_form_phrase');
            $('#search').click(function(){
                $(this).addClass( 'active' );
                if( searchBox.val() == 'Search'){
                     searchBox.val('');
                }
            });
            searchBox.change(function() {
                $('#search').removeClass( 'active' );
                if( searchBox.val() == ''){
                    searchBox.val('Search')
                }
            }).blur(function(){
                $('#search').removeClass( 'active' );
                if( searchBox.val() == ''){
                    searchBox.val('Search')
                }
            });

            var speed = 100;
            var serchBox = $('#search');

            $('#searchNav').click(function(){
                var my = $(this);
                if( serchBox.css('display') == "block" ){
                    serchBox.slideUp( speed );
                    my.removeClass( 'active' );
                }else{
                    serchBox.slideDown( speed );
                    my.addClass( 'active' );
                }
            })
        },


        setHome : function()
        {

            var device = this.getDeviceFromWidth();
            $('#om').click(function(e){
                e.preventDefault();
                var url = '';
                if( device == _DEVICE_PC ){
                    url = BASE_DIRECTORY;
                }else if( device == _DEVICE_TAB ){
                    url = BASE_DIRECTORY + 'tablet/';
                }else if( device == _DEVICE_SP ){
                    url = BASE_DIRECTORY + 'sp/';
                }
                location.href= url;
            });
        },

        setTabMenu :function()
        {
            var li = $('div.tabGroup div.tab li');
            li.eq( 0 ).addClass('active');
            li.click(function(e){
                e.preventDefault();
                var index = $(this).index();
                Library.showTabInner( index );
                $(this).closest('ul').children('li').removeClass('active');
                $(this).addClass('active');
            });
        },

        showTabInner: function( index )
        {
            var uls = $('div.tabGroup div.tabInner > ul');
            var cnt = uls.length;
            for( var  i=0; i<cnt; i++ ){
                var ul = uls[i];
                var lis = $(ul).children('li');
                lis.hide();
                lis.eq(index).fadeIn( 300 );
            }
        },

        setL2title: function()
        {
            var hh = $('#header').height() ;
            var dh = $('div.l2Title').height() ;
            var scroll = $(window).scrollTop();
            if($('div.titleClone').length == 0){
                var titleClone = $('<div class="titleClone">TITLE</div>');
                titleClone.css({
                    'display':"none",
                    'background':'#777',
                    'color':'#fff',
                    'padding':'6px',
                    'font-weight':'bold',
                    'position': 'fixed',
                    'top': hh,
                     "width": '100%'});
                $('#container').prepend(titleClone)
            }
            $('div.l2Title').each(function(i){

                var myTop = $(this).offset().top;
                var myIndex = $(this).index();
                if( scroll + hh > myTop && scroll + hh < $('div.l2Title').eq(i+1).offset().top ){
                    var t = $(this).html();
                    $('div.titleClone').show().html( t );
                }
            });
            if( scroll <= $('#header').outerHeight() ){
                $('div.titleClone').hide();
            }
        },

        // 2022.12.21 rewrite
        setAnchor: function()
        {
            var hash = location.hash;
            var targetId = hash.replace('#', '');
            var speed = 300;

            // load page & scroll
            if( $("[id ='"+ targetId +"' ]").length > 0 ){
                var top =  $("[id ='"+ targetId +"' ]").offset().top;
                $('body,html').animate({scrollTop:top - $('#header').height() - 30 }, speed, 'swing');
            }
            if( $("[name ='"+ targetId +"' ]").length > 0 ){
                var top =  $("[name ='"+ targetId +"' ]").offset().top;
                $('body,html').animate({scrollTop:top - $('#header').height() - 30 }, speed, 'swing');
            }


            // hash link
            $('a[href*=#]').click(function(e) {

                let href = $(this).attr("href");
                let list_hash = href.slice(1).split('#');
                let $target = '';
                if( href.indexOf('#') >= 0){
                    let $name_target = $("a[name="+ list_hash[list_hash.length - 1] +"]");
                    let $id_target = $("#"+ list_hash[list_hash.length - 1]);
                    if( $name_target.length > 0 ){
                        $target =$name_target;
                    }else if($id_target.length > 0 ){
                        $target = $id_target;
                    }
                    if( $target.length > 0){
                        //this page
                        let pos = $target.offset().top;
                        $('body,html').animate({scrollTop:pos - $('#header').height() - 30 }, speed, 'swing');
                    }
                }else{

                }
            });
        },

        setPageBottomPadding: function()
        {
            if( $('body#interior').length == 0 && $('body#appearance').length == 0  ){
                var targetBottom = $('#footer').outerHeight();
                if( this.getDeviceFromWidth() == _DEVICE_PC){
                    targetBottom +=20;
                }
                $('div#container').css({'padding-bottom': targetBottom + 'px'});
            }
        },

        setH1Prev : function (){
            var speed = 300;
            var my = this;
            if( $('h1.has_prev').css('background-image') != "none" ){
                $('h1.has_prev').click(function(){
                    if( document.referrer == ""){
                        if( _DEVICE_TAB == my.getDeviceFromWidth()){
                            location.href = "../tablet/index.html"
                        }else if( _DEVICE_SP == my.getDeviceFromWidth()){
                            location.href = "../sp/index.html"
                        }else{
                            location.href = "../index.html"
                        }
                    }else{
                        my.goPrev();
                    }
                })
            }
        },

        goPrev: function ()
        {
            history.back(-1);
        },

        //スマフォにおいて、立て向きか横向きかを取得 pcで使用する事はない仮定
        getDeviceDirection :function()
        {
            return ( $( window ).width() > $( window ).height() )? this.DIRECTION_YOKO : this.DIRECTION_TATE;
        },

        preload : function( list ){
            for(var i = 0; i< list.length; i++){
                $("<img>").attr("src", list[i]);
            }
        },

        setZoomAction :function()
        {
            var my = this;
            $("body").on("gesturechange", function(e){
                var zoomScale = document.body.clientWidth / window.innerWidth;
                //pc 表示の場合

                /*console.log($('#nav').css('display')); 2022.07.04 */
                if( $('#nav').css('display') == "block" && $('#tabNav').css('display') == "none" ){
                    my.myScale *= e.originalEvent.scale;
                    if( zoomScale <= 1){
                        my.myScale = 1;
                        //'use strict';
                        $('body').removeClass('is_zoom');
                        $('#nav').css({'position': 'fixed'});
                        $('#header').css({'position': 'fixed'});
                        my.setNavHeight();
                    }else{
                        if($('#nav').css('display') == 'block'){
                            $('body').addClass('is_zoom');
                            $('#nav').css({'position': 'static', 'height':'auto'});
                            $('#header').css({'position': 'static'});
                        }
                    }
                }
            });
        },

        //2018.02.05 change
        setSearchBoxFormAction: function()
        {
            var my = this;
            var searchBox = $('#MF_form_phrase');
            $('#search input.b').click(function(e){
                e.preventDefault();
                if( searchBox.val().indexOf('Search') >= 0 || searchBox.val() == '' ){
                    searchBox.val('Search');
                    $('#search').removeClass( 'active' );
                    return false;
                }
                my.makeSearchWord();
            });

        },

        makeSearchWord: function()
        {
            var original_phrase =  $('#search input#MF_form_phrase').val();
            if( phrase == "Search" || phrase == ""  ){
                return
            }

            original_phrase = original_phrase.replace( CAR_NAME ,'');
            original_phrase = original_phrase.replace( CAR_TYPE ,'');

            var phrase = original_phrase + ' ' + CAR_NAME + ' ' + CAR_TYPE;
            $('#search input#MF_form_phrase').val(phrase);
            $('#search form').submit();
            $('#search input#MF_form_phrase').val(original_phrase);
        },

        isPhone : function()
        {
            return (navigator.userAgent.indexOf('iPhone') > 0 || navigator.userAgent.indexOf('Android') > 0);
        },

        //スマホの時だけtelリンクを有効にする 2016.05.30
        // 調整 2017.05.23
        setTelLink : function(){
            if( Library.isPhone() ){
                $('span[data-action=call]').each(function() {
                    var $ele = $(this);
                    $ele.wrap('<a href="tel:' + $ele.data('tel') + '" style="background-position:3px 6px"></a>');
                });
            }
        },


        // 2017.07.19 update
        // 2018.08.24 update
        setP2Link:function()
        {
            // main contents & recommend
            $('.main .inner a[href], .relationItem a').each(function(){
                var url = $(this).attr('href');
                if( !$(this).hasClass('outOfOm') ){
                    return false;
                }
                var href = url.split('/').pop();
                var hrefList = href.split('#');
                var fileName = hrefList[0];
                var hash = hrefList[1];

                if( MENU.split(fileName).length-1 > 1 && fileName.indexOf('?p') < 0 ){
                    var targetURL = fileName  + '?p2';
                    if( hash ){
                        targetURL += '#' + hash;
                    }
                    $(this).attr({'href':  targetURL });
                }
            });
        },

        // 2018.08.16 update
        setSlick:function()
        {
            if( $('.slider').length > 0 ){
              $('.slider').on('init',function(){
                    $('.slider').hide().height('auto').slideDown( 300 ).animate({ 'opacity': 1 }, 300);
              });
                var $slider = $('.slider').slick({
                  dots: false,
                  infinite: true,
                  speed: 500,
                  fade: false,
                  cssEase: 'linear'
              });



            }
        },

        agreement: (function()
        {
            return{
                cValue : 'true',
                cancelMessage: "使用承諾書および個人情報使用同意書をキャンセルしますか？",
                agreementFile: "agreement.html",
                savepath: "/ownersmanual/",
                PLATFOMRS: [
                    'Y!J-SRD'
                    ,'Y!J-MBS/1.0'
                    ,'Yahoo! Slurp'
                    ,'Yahoo! DE Slurp'
                    ,'Googlebot-Mobile/'
                    ,'Googlebot/'
                    ,'adsence-Google'
                    ,'msnbot'
                    ,'bingbot/'
                    ,'Hatena'
                    ,'MicroAd/'
                    ,'Baidu'
                    ,'MJ12bo'
                    ,'Steeler'
                    ,'YodaoBot'
                    ,'OutfoxBot'
                    ,'Pockey'
                    ,'psbot'
                    ,'Yeti/'
                    ,'Websi'
                    ,'Wget/'
                    ,'NaverBot'
                    ,'BecomeBot'
                    ,'heritr'
                    ,'DotBot'
                    ,'Twiceler'
                    ,'ichiro'
                    ,'archive.org_bot'
                    ,'YandexBot/'
                    ,'ICC-Crawler'
                    ,'SiteBot/'
                    ,'TurnitinBot/'
                    ,'Purebot/'
                ],
                showAgreement: function( callback )
                {

                    var my = this;
                    if (this.isAlreadyAgreed() == true) {
                        return;
                    }

                    if (window.MF_CAPTURE) {
                        return true;
                    }
                    if (this.isCrawler() == true) {
                        return;
                    }
                    var agreementDom = $('<div>').attr('id', 'agreementDiv');
                    $("body").prepend( agreementDom );
                    //pc トップのみ、agreementFileのパスを変更
                    $.ajax({
                        type: "GET",
                        url:  BASE_DIRECTORY + this.agreementFile,
                        //dataType: "text",
                        success: function (data) {
                            $("#agreementDiv").html( data );

                            //agree の高さ設定
                            var agreeHeight = Math.round($(window).height() * 0.8 - 120);
                            $("#feedback div.agreeInner").css({ height:agreeHeight});

                            my._setShowAgreement( callback );
                            //iOS-iPhoneによるバグ対策
                            $("#feedback div.agreeInner").hide().slideDown(300,function(){ $(this).css({'overflow': 'auto'}) });
                        },
                        error: function () {
                            $("#agreementDiv").html('読み込みに失敗しました');
                        }
                    });
                },
                _setShowAgreement: function ( callback ) {
                    var my = this;

                    $('#agreementDiv div').slideDown();
                    // 同意書を表示するボタン
                    /*
                    $('#agreementDiv div.agreement a').click(function (e) {
                        e.preventDefault();
                        $('.agreement_box_container').show(0, function () {
                            $('.agreement_box').animate({ top: '15px' }, 300, 'swing');
                        });
                    });
                    */
                    // キャンセルボタン
                    $('#agreementDiv span#submitCancel').click(function (e) {
                        e.preventDefault();
                        $('#agreementDiv div.agreement').animate({ top: '-440px' }, 300, 'swing', function () {
                            my.cancelButton();
                        });
                    });
                    // 同意しますボタン
                    $('#agreementDiv span#submitAgree').click(function (e) {
                        e.preventDefault();

                        //2025.02.28
                        //Cookieに保存します。
                        //$.cookie( my.getKey( BASE_DIRECTORY ), my.cValue, { path:my.savepath, expire:""} )

                        //2026.01.06 Cookie secure対策
                        //$.cookie( my.getKey(), my.cValue, { path:my.savepath, expire:""} )
                        $.cookie(
                            my.getKey(),
                            my.cValue,
                            {
                                path: my.savepath,
                                expires: "",
                                secure: true
                            }
                        )

                        $('#agreementDiv').fadeOut(300, function(){ callback() });
                    });

                },
                //既に、使用承諾書に同意してもらったかどうか？の判定
                isAlreadyAgreed: function () {
                     //2025.02.28
                    //var key = this.getKey( BASE_DIRECTORY );
                    var key = this.getKey( );
                    if ( $.cookie( key ) === "true" ) {
                        return true;
                    }
                    return false;
                },
                //クライアントが、クローラかどうかの判定
                isCrawler: function () {
                    var userAgent = window.navigator.userAgent;

                    if (userAgent == "") {
                        return true;
                    }
                    for (var i = 0; i < this.PLATFOMRS.length; i++) {
                        var Platform = this.PLATFOMRS[i];
                        if (userAgent.indexOf( Platform ) >= 0) {
                            return true;
                        }
                    }

                    /*
                    if (userAgent.indexOf("opera") >= 0) {
                        return false;
                    }
                    else if (userAgent.indexOf("mozilla") >= 0) {
                        //クローラかどうかの判定を行います。
                        for (var i = 0; i < this.PLATFOMRS.length; i++) {
                            var Platform = this.PLATFOMRS[i];
                            if (userAgent.indexOf( Platform ) >= 0) {
                                return false;
                            }
                        }
                        return true;
                    }
                    */
                },
                //同意書で、承諾ではなく、[キャンセル]ボタンが押された時のイベント
                cancelButton: function ()
                {
                    history.back();
                },
                //2025.02.28
                getKey : function( str )
                {
                    return _COOKIE_AGREEMENT;
                    //return str.replace( /\//g , '');
                }
            }

        }())


//
    }
}());


////////////////////////////////////////////

//UAチェック
Library.setLocation();

jQuery(function ($) {

    Library.setHome();
    if( location.href.indexOf('http') >= 0 ){
        Library.agreement.showAgreement(
            function(){
                if(typeof startUp == "function"){startUp()}
            }
        );
    }


    // DOM育成 window load後処理
    $(window).load(function(){
        Library.setTabMenu();
        Library.showTabInner(0);
        Library.setAnchor();
        Library.setPageBottomPadding();
        Library.setSearchNav();
        Library.setSearchBoxFormAction();
        Library.setZoomAction();
        Library.setTelLink();
        Library.setP2Link();
        Library.setSlick();
        setTimeout(function(){  //2025.02.10
            Library.setSearchFilter(); 
        },300)
    });

    var timer ;
    $(window).resize(function() {
        if (timer !== false) {
            clearTimeout(timer);
        }
        timer = setTimeout(function() {
            Library.setHome();
            Library.setPageBottomPadding();
        }, 200);
    });

    $(window).scroll(function(){
        Library.setL2title();
        Library.setScrollPosition();
    });
});

//for IE8
if (!Array.indexOf) {
    Array.prototype.indexOf = function(o) {
        for (var i in this) {
            if (this[i] == o) {
                return i;
            }
        }
        return -1;
    }
}

