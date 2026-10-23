/**
 * jquery point
 * ex
 * $('#sub_navi ul').point({selectIndex:2});
 *
 * last update 2018.10.29
 */

;(function($) {
	$.point = function(element, options) {

		var defaults = {
			pointList: []
		}

		var plugin = this;
		plugin.settings = {}

		var $element = $(element),
		element = element;

		////////////////////////////////////////////

		var _dataList ;

		var _timer = false;
		var _grip = $('#grip');

		var _selectedPoint = 333333 ;

		var _stock = [];


		////////////////////////////////////////////
		//public
		plugin.init = function() {
			plugin.settings = $.extend({}, defaults, options);
			_dataList = options.pointList;
			_add();
			_setGraphic();

			$(window).resize(function() {
				if (_timer !== false) {
					clearTimeout(_timer);
				}
				_timer = setTimeout(function() {
					_setPosition();
				}, 200);
			});
			$(window).scroll(function () {

			});
		}

		plugin.closePop = function(){
			_closePop();
		}

		////////////////////////////////////////////
		//private
		/**
		*
		*/
		var _add = function(){
			//ポイント設定
			var cnt = _dataList.point.length;
			for(var i=0; i<cnt; i++){
				var point = _dataList.point[i];
				var div = _setPoint( point , $(element));
				_dataList.point[i].div = div;
			}

			//ズーム設定
			if(_dataList.zoom){
				cnt = _dataList.zoom.length;
			}else{
				cnt = 0;
				setTimeout(function(){
					_setPosition();
				},100)
			}
			for(var i=0; i<cnt; i++){
				var zoom = _dataList.zoom[i];
				var items = point.items;
				var src = zoom.src;
				var img = new Image();

				var ua = navigator.userAgent;
				var isIE8 = ua.match(/msie [8.]/i);

				if( isIE8 && $(img).width() !=0 ) {
					_setPosition();
				}else{
					//対象画像を先に読み込まないと、xy座標が算出できない
					var loaderCnt = 0;
					img.onload = (function( zoomData ,i , cnt ){

						return function(e){

							var imgPath = $(this).attr('src');
							var zoomDiv = $('<div class="zoom"></div>');
							zoomData.div = zoomDiv;

							//zoom先指定
							var zoomTargetDiv = $('<div class="zoomImg" id=""><div class="imgTarget"></div></div>');
							var zoomTargetInnerDiv = zoomTargetDiv.find( 'div.imgTarget' );

							zoomTargetInnerDiv.css('background-image', 'url('+ imgPath +')');
							$('#graphic').prepend( zoomTargetDiv );
							//$('#screen').prepend( zoomTargetDiv );	// only pc
							$(element).prepend( zoomDiv.hide() );
							_getGraphicPosSize( 640, 943 );

							zoomDiv.on("click",{ target: zoomTargetDiv }, _zoomHandler );
							zoomTargetDiv.click(function(){
								if($('#pop').css('display') == "block"){
									_closePop();
								}else{
									$(this).fadeOut();
								}
							});

							zoomData.divTarget = zoomTargetDiv;

							//console.log($(e.target)[0].width);
							var imgSize = new Object();
							imgSize.w =  $(this)[0].width;
							imgSize.h =  $(this)[0].height;
							zoomData.size = imgSize;

							var pointCnt = zoomData.point.length;
							for(var j=0; j<pointCnt; j++){
								var zoomPoint = zoomData.point[j];
								zoomPoint.div = _setPoint( zoomPoint, $(zoomTargetInnerDiv) );
							}
							loaderCnt++;
							if( loaderCnt == cnt){
								//最後の画像読み込み時に、ポジションを設定
								setTimeout(function(){
									_setPosition();
									_imageLoaded();
								},100)
							}
						}
					})( _dataList.zoom[i] , i ,cnt );
					img.src = src;
				}
			}
			/*
			$('img.carPhoto').click(function(){
				_closePop();
			});
			*/

		}

		var _setPoint = function( point , target )
		{
			//var caption = point.caption;
			//var url = point.url;
			var div = $('<div/>').addClass('point');
			target.prepend( div.hide() );

			var items = point.items;
			var itemsLength = items.length;
			var fukidashiDom = $('<div>');
			for(var i=0; i<itemsLength; i++){
				var item = items[i];
				//2018.10.29
				//var itemDom = $('<a>').attr('href', item.url).text(item.caption);
				var itemDom = $('<a>').attr('href', item.url).html(item.caption);
				fukidashiDom.append( itemDom );
			}

			var my = this;

			div.on({
					'mouseenter':function( e ){
						_pop(e , fukidashiDom, $(this).offset());
						$(this).addClass('hover');
						_selectedPoint = $(this);
					}
					,'mouseleave':function( e ){
						_closePop();
						$(this).removeClass('hover');
					}
				})
			$('#pop').on({
					'mouseenter':function( e ){
						$(this).show();
						$(_selectedPoint).addClass('hover');
					}
					,'mouseleave':function( e ){
						_closePop();
						$(_selectedPoint).removeClass('hover');
					}
				})
			return div;
		}

		//ポイントとズームに対して、場所を設定
		var _setPosition = function()
		{
			var carPhoto = $($element.find('img.carPhoto'));
			var w = carPhoto.width();
			var h = carPhoto.height();

			//point
			var points = _dataList.point;
			var cnt = points.length;

			var offsetTop = parseInt( $($element.find('img.carPhoto')).css('margin-top') );
			var offsetLeft = parseInt( $($element.find('img.carPhoto')).css('margin-left') );

			if( !offsetTop ){
				offsetTop = 0 ;
			}
			if( !offsetLeft ){
				offsetLeft = 0 ;
			}

			for(var i=0; i<cnt; i++){
				var point = points[i];
				var pointDiv = point.div.show();
				_setPointPosition( point , pointDiv ,w ,h, offsetTop, offsetLeft );
			}
			//zoom
			if(_dataList.zoom){
				var zooms = _dataList.zoom;
				cnt = zooms.length;
			}else{
				cnt = 0;
			}

			for(var i=0; i<cnt; i++){
				var zoom = zooms[i];
				var zoomDiv = zoom.div;
				var x = w * zoom.x;
				var y = h * zoom.y;
				var zoomW = w * zoom.w;
				var zoomH = h * zoom.h;
				var zoomImgSize = zoom.size;
				zoomDiv.css({ top: y ,left: x, width:zoomW, height: zoomH  }).show();
				var zoomPoints = zoom.point;
				var pointCnt = zoomPoints.length;

				for(var j=0; j<pointCnt; j++){
					var zoomPoint = zoomPoints[j];
					var zoomPointDiv = zoomPoint.div.show();
					var targetSize = _getGraphicPosSize( zoomImgSize.w, zoomImgSize.h);
					_setPointPosition( zoomPoint , zoomPointDiv ,targetSize.w ,targetSize.h, targetSize.top, targetSize.left);
				}
			}
			//zoom target
			$("div.zoomImg").width( $('#graphic').width() )	
			//$("div.zoomImg").width( $(window).width() )	//only pc
		}

		//ポイントひとつに対して、場所を設定
		var _setPointPosition = function( point, targetDiv ,w, h, top, left )
		{
			var marginTop = 0;
			var marginLeft = 0;

			if( top ){
				marginTop = top;
			}
			if( left ){
				marginLeft = left;
			}

			var pointH = $('div.point').height();
			var pointW = $('div.point').width();
			//ポイントの起点を中心に考える
			var x = w * point.x + marginLeft - pointH/2;
			var y = h * point.y + marginTop - pointW/2;
			targetDiv.css({ top: y ,left: x });
		}
		//ポイントクリック時のハンドラー
		var _pointHandler = function(e)
		{
			var my = $(e.target);
			if( my.hasClass('active') ){
				closePop();
				$('div.point').removeClass('active');
			}else{
				$('div.point').removeClass('active');
				_pop( e );
			}
		}

		//ふきだしpopを表示
		var _pop = function(  e, captionDom,  offset  )
		{
			e.stopPropagation();
			//$('#graphic ul.changeView li img.carPhoto').css({'opacity': 0.5});

			//サイズを初期化
			$('#pop').width( 'auto' );

			//データ反映
			$('#pop div.popInner span').html( captionDom );

			$('#pop').show();
			//ひとまず0で、高さを算出
			$('#pop').css({left:0, top: 0})

			if( $('#pop').outerWidth() > $(window).width()*0.8 ){
				$('#pop').width($(window).width()*0.8) ;
			}

			var padding = 20;
			var pointW = 48
			var w = ( $('#pop').outerWidth() - pointW ) / 2;
			var h = $('#pop').outerHeight();

			var marginY = -7;

			//上側
			var targetLeft = offset.left - w ;
			var targetTop = offset.top - h - marginY ;

			//下側
			if( targetTop < $('#header').outerHeight() + $('h1').outerHeight() ){
				targetTop = offset.top + marginY + pointW;
			}

			if(targetLeft < 4){
				targetLeft = 4;
			}
			if(targetLeft + $('#pop').outerWidth()  >  $(window).width()){
				targetLeft = $(window).width() - $('#pop').outerWidth();
			}
			$('#pop').css({left:targetLeft, top: targetTop})

			//グリップ調整
			_setGripPosition( offset.left - targetLeft + pointW/2 -3, offset.top - targetTop + pointW/2 );

			$(e.target).addClass('active');
		}

		//popのつまみ部分の場所設定
		var _setGripPosition =  function( x , y )
		{
			var gripY =  -_grip.height();

			if( y < 0 ){
				-_grip.addClass('upper');
				_grip.css({'top': -_grip.height(),'bottom':'auto'});
			}else{
				-_grip.removeClass('upper');
				_grip.css({'bottom': -_grip.height(),'top':'auto'});
			}
			_grip.css({'left': x - _grip.width()/2 + 3});
		}

		//popを閉じる
		var _closePop = function( e )
		{
			//$('#graphic ul.changeView li img.carPhoto').css({'opacity': 1});
			$('div.point').removeClass('active');
			$('#pop').hide();
		}

		var _setGraphic = function(){
			$('#graphic ul.changeView li').click(function(){
				_closePop();
			})
		}

		var _getGraphicSize = function()
		{
			var size = new Object();
			/*
			if( $('#graphic').length > 0){
				size.h = window.innerHeight
					- $('#container h1.has_prev').outerHeight()
					- $('#header').height() ;
			}
			size.w = $(window).width();
			*/
			size.w = $('#graphic').width();
			size.h = $('#graphic').height();
			// only pc
			//size.w = $('#screen').width();
			//size.h = $('#screen').height();
			return size;
		}

		var _zoomHandler = function( e ){
			e.data.target.fadeIn();
			_closePop();
		}

		var _imageLoaded = function()
		{
			$('#graphic').css({'background': '#222'});
		}

		//背景画像を指定した画像(background:contain)が親div の中で、幅、高さがいくつに設定されているか
		var _getGraphicPosSize = function( w, h )
		{

			var targetSize = new Object();
			targetSize.left = 0;	 //左右センターの場合の右側からの位置
			targetSize.top = 0;		 //上下ミドルの場合の上側からの位置

			var gW =  _getGraphicSize().w;
			var gH = _getGraphicSize().h;

			if( w/h > 1){
				//横長
				targetSize.h =  Math.floor( h * ( gW / w ));
				targetSize.w =  gW;
				targetSize.top = Math.floor(( gH - targetSize.h )/2);
			}else{
				//縦長 - 高さを合わせる
				targetSize.h = gH;
				targetSize.w = Math.floor( w * ( gH / h ));
				targetSize.left = Math.floor(( gW - targetSize.w )/2);
			}
			return targetSize;
			//console.log(targetSize);
		}

		//init
		plugin.init();
	}


	$.fn.point = function(options) {
		return this.each(function() {
			 if ( undefined == $(this).data( 'point' ) ) {
				var plugin = new $.point(this, options);
				$(this).data('point', plugin);
			}
		});
	}

})(jQuery);
