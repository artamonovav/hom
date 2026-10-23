/**
 * jquery interior
 * ex
 * $('#sub_navi ul').interior({selectIndex:0});
 *
 * last update 2018.08.27
 */

;(function($) {
    $.interior = function(element, options) {

        var defaults = {
            selectIndex: 0
        }

        var plugin = this;
        plugin.settings = {}

        var $element = $(element),
        element = element;

        ////////////////////////////////////////////

        /*
        var _selectIdx;
        var _maxRight = [];
        var _maxRightIdx = [];
        var _scrollIdx = [];
        */

        var _is_lock;
        var _selectIdx;
        var _distance;
        var _myX = [];  //現在のx移動値
        var _maxRight = []; //左移動時の最大px
        //var _scrollIdx = [];
        var _timer = false;
        var _MODE_INDOOR = 0;   //ul.changeView li:first-child - 室内
        var _MODE_SEAT = 1;     //ul.changeView li:last-child - シート

        ////////////////////////////////////////////
        //public
        plugin.init = function() {
            plugin.settings = $.extend({}, defaults, options);

            _selectIdx = 0;
            _selectIdx = options.selectIndex;
            _distance =  $('#graphic').width();
            _setSize();
            _setNav();
            _selectView( _selectIdx );
            _is_lock = false;

            /*
            _scrollView(_maxRight[_selectIdx] , 0 );
            _myX[_selectIdx] = _myX[_selectIdx] - _distance;
            _checkNavVisible();
            */
        }

        ////////////////////////////////////////////
        //private
        /**
        *
        */
        var _setSize = function(){

            //表示領域の高さ
            var innerHeight = $('#graphic').innerHeight;
            var targetH = window.innerHeight
                - $('#container h1.has_prev').outerHeight() 
                - $('#header').height();

            $element.find('li').each(function( i ){
                var img = $(this).find('img');

                img.height( innerHeight );
                img.width( 'auto' );
                var imgWidth = img.width();
                $(this).width( imgWidth );
                $('#graphic').removeClass('is_yoko');

                _checkNavVisible();

                _maxRight[i] = -( imgWidth - $('#graphic').width());

                _myX[i] = 0;

            });
        }

        var _setNav = function (){
            //前方後方
            $('#frontRearView li').click(
                function(){
                    var idx = $(this).index();
                    _selectNav( idx );
                    _selectView( idx  );

                    if( $(this).index() == 0 ){
                        history.replaceState('', document.title, window.location.pathname);
                    }else{
                        _selectView( idx );
                        var hashString = '#seat'
                        history.replaceState('', document.title, window.location.pathname + hashString);
                    }
                    //scrollIdx を調整しないといけない
                }
            );
            //初期値セット
            _selectNav( _selectIdx );

            _checkNavVisible();

            //左右スクロール
            $('#horizontalScroll li:first-child').click(
                function(){
                    if( !_is_lock){
                        _is_lock = true;
                        _scrollPrev();
                    }
                }
            );
            $('#horizontalScroll li:last-child').click(
                function(){
                    if( !_is_lock){
                        _is_lock = true;
                        _scrollNext();
                    }
                }
            );
        }

        var _selectNav = function( idx )
        {
            var nav_li = $('#frontRearView li');
            nav_li.removeClass('active');
            $(nav_li[ idx ]).addClass('active');
        }

        //右へ
        var _scrollNext =  function( )
        {
            var speed = 500;

            if( _myX[_selectIdx] == _maxRight[_selectIdx]){
                /*
                if( _selectIdx == _MODE_INDOOR ){
                    //最右 室内からシートへ切り替え
                    _selectIdx = _MODE_SEAT;
                    _selectNav( _selectIdx );
                    _selectView( _selectIdx);
                }
                */
            }else{
                if( _myX[_selectIdx] - _distance >= _maxRight[_selectIdx] ){
                    //動作
                    _myX[_selectIdx] = _myX[_selectIdx] - _distance;
                    _scrollView(_myX[_selectIdx] , speed );
                }else{
                    //最右へ
                    _scrollView(_maxRight[_selectIdx] , speed );
                }
                _myX[_selectIdx] = _myX[_selectIdx] - _distance;
            }
        }

        //左へ
        var _scrollPrev = function( )
        {
            var speed = 500;
            if( _myX[_selectIdx] == _MODE_SEAT ){
                //室内からシートへ切り替え
                /*
                if( _selectIdx == _MODE_INDOOR ){
                    _selectIdx = 0;
                    _selectNav( _selectIdx );
                    _selectView( _selectIdx );
                }
                */
            }else{
                if( Number(_myX[_selectIdx]) + _distance <= 0 ){
                    _myX[_selectIdx] = Number(_myX[_selectIdx]) + _distance;
                    _scrollView( _myX[_selectIdx] , speed);
                }else{
                    //最左 室内からシートへ切り替え
                    _myX[_selectIdx] = 0;
                    _scrollView( 0 , speed);
                }
            }
        }

        //スクロールさせる
        var _scrollView =function( x , speed )
        {
            //動かす
            $('#interior #graphic ul.changeView li').eq( _selectIdx ).trans(
                {x: x}, speed, 'easeOutExpo', function(){}
            );
        }

        $.fn.trans = function( xyList, speed, easing, callback ) {
            $.support.transition = typeof $("body").css("transitionProperty") === "string";
            if($.support.transition){
                this.transition(
                    { x : xyList.x , y: xyList.y }, speed, easing, function(){
                        callback();
                        _checkNavVisible();
                     }
                );
            }else{
                this.animate( { 'left' : xyList.x , "top": xyList.y }, speed, easing,function(){ callback();_checkNavVisible(); } );
            }
            return this;
        };


        /**
        *   ナビの表示/非表示
        */
        var _checkNavVisible = function (){

            if( _myX[ _selectIdx ] >= 0 ){
                $('#horizontalScroll li:first-child').hide();
            }else{
                $('#horizontalScroll li:first-child').fadeIn(300);
            }

            if( _myX[ _selectIdx ] <= _maxRight[ _selectIdx ] ){
                $('#horizontalScroll li:last-child').hide();
            }else{
                $('#horizontalScroll li:last-child').fadeIn(300);
            }
            _is_lock = false;
        }

        var _selectView = function( idx ){

             _selectIdx = idx;
            if( _selectIdx == _MODE_INDOOR ){
                _scrollView( _maxRight[_selectIdx] , 0 );
                _myX[_selectIdx] = _maxRight[_selectIdx];
            }else if( _selectIdx == _MODE_SEAT ){
                _scrollView( 0, 0 );
                _myX[_selectIdx] = 0;
            }

            var view_li = $element.find('li');
            view_li.removeClass('active');
            $(view_li[ idx ]).addClass('active').hide().fadeIn( 200 );
            _checkNavVisible();
        }

        // css3 transition におけるx 取得
        _matrixToArray = function (str) {
          return str.match(/(-?[0-9\.]+)/g);
        }
        _getX = function (list ) {
          return _matrixToArray(list)[4];
        }

        //init
        plugin.init();
    }

    $.fn.interior = function(options) {
        return this.each(function() {
             if ( undefined == $(this).data( 'interior' ) ) {
                var plugin = new $.interior(this, options);
                $(this).data('interior', plugin);
            }
        });
    }


})(jQuery);
