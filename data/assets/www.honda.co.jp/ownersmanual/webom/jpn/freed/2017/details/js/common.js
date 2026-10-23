
/**
* update 2025.03.10 URL parameters / adjust nav setting
*/
/* GAログテストコードあり */

is_flickHistory = true;

jQuery(function ($) {
	var timer = false;
	$(window).load(function(){

		Library.setNav();
		Library.setMore();
		Library.setH1Prev();
		
		setTabNav();
		initMedia();
		setNavActiveCurrent();
		setAlert();
		startAnimation();
		//setSelectURL();

		if( typeof b_playerWidth != 'undefined' && typeof b_playerHeight != 'undefined'){
			setMovieSize( b_playerWidth, b_playerHeight );
		}
		setNavScroll();
		setEdition();

		$(window).resize(function() {
			if (timer !== false) {
				clearTimeout(timer);
			}
			timer = setTimeout(function() {
				initMedia();
				if( typeof b_playerWidth != 'undefined' && typeof b_playerHeight != 'undefined'){
					setMovieSize( b_playerWidth, b_playerHeight );
				}
			}, 200);
		});

		$(window).scroll(function () {
			
		});
		
	//load
	});

	var initMedia = function()
	{
		/* add 2022.07.04
		if( $(window).width() >= Library.WIDTH_TAB ){
			$('#nav').show().transition({x:0,y:0},0);
			Library.setNavHeight();
		}
		if( $(window).width() < Library.WIDTH_TAB && $(window).width() > Library.WIDTH_SP ){
			hideNav( 0 );
			Library.setNavHeight();
		}
		*/
		if( $(window).width() < Library.WIDTH_TAB ){	/* add 2022.07.04 */
			hideNav( 0 );
		}else{
			$('#nav').show().transition({x:0,y:0},0);
		}
		Library.setNavHeight();
	}

	//////////////////////////////////
	// menu scroll
	//
	
	var setNavScroll = function()
	{
		$('#nav li').each(function(){
			if($(this).hasClass('active')){
				var top = Math.round( $(this).offset().top - $('#nav').offset().top );
				$('#nav').scrollTop( top );
				return false;
			}
		});
		
	}
	
	//////////////////////////////////
	// for movie
	// movie は、動的にリサイズできないので、SP/TABLET 時、縦横、短い方に合わせる
	var setMovieSize = function( w, h)
	{
		var movieObj = $('div.movie object ,div.movie iframe');

		ratio = w/h;
		var targetW = $('div.movie').width();
		var targetH = targetW / ratio;

		movieObj.css( {'width': targetW });
		movieObj.css( {'height':targetH });
	}
	
	//////////////////////////////////
	// for TABLET
	var setTabNav = function ( is_show )
	{
		var nav = $('#nav');
		 $('#tabNav').click(function(){
			if( nav.css('display') == "block"){
				//nav.animate({left: -$('#nav').width() },0,function(){ $(this).hide(); });
				hideNav();
			}else{
				//nav.show().animate({left: 0}, 300);
				showNav()
			}
		});
		$('#tabNav').hover(
			function(){
				$(this).addClass('hover');
			},
			function(){
				$(this).removeClass('hover');
			}
		);
		/*
		if(!is_show){
			nav.transition({x: -$('#nav').width() }, 0,function(){ $(this).hide(); });
			$('#tabNav').removeClass( 'active' );
		}
		*/
	}
	var hideNav = function ( speed ){
		if( speed == 'undefined' ){
			speed = 300
		}
		$('#nav').transition({x: -$('#nav').width() }, speed,function(){ $(this).hide(); });
		$('#tabNav').removeClass( 'active hover' );
	}
	var showNav = function ( speed ){
		if( speed == 'undefined' ){
			speed = 300
		}
		$('#nav').show().transition({x: 0}, speed);
		$('#tabNav').addClass( 'active' );
	}
	//////////////////////////////////
	// edition 車両仕様
	var setEdition = function()
	{
		$("#user_spec select").change(function() {
			var index = $(this).val();
		        var targets = $('div.selectList div.selectTarget').hide();
		        $('div.selectList').each(function () {
		            $(this).children('div.selectTarget').eq(index).fadeIn();
			});		
		});
	}
	//////////////////////////////////
	// alert
	var setAlert = function()
	{
		$("#warning_list li a").tile();
		$("#warning_list .warning_list_icon").tile();
	}

	//////////////////////////////////
	// アニメーション
	var startAnimation = function()
	{
	  if ($('.description_images').length >= 1) {
		$('.description_images p').hide();
		$('.description_images p:first').show();
		$('.description_images p:first').addClass('current');
		setInterval(function() {
		  if ($('.description_images p.current').next().length == 0) {
			// 最初に戻るまで待つ
			for (var i = 0 ; i < 10 ; i++) {
			  if (!$('.description_images p.current').hasClass('wait' + i)) {
				$('.description_images p.current').addClass('wait' + i);
				return;
			  }
			}
			for (var i = 0 ; i < 10 ; i++) {
			  $('.description_images p.current').removeClass('wait' + i);
			}
			$('.description_images p.current').hide().removeClass('current');
			$('.description_images p:first').show().addClass('current');
			return;
		  }
		  $('.description_images p.current').hide().removeClass('current').next().show().addClass('current');
		}, 250);
	  }
	 }
	//////////////////////////////////
	/*
	var setSelectURL = function(){
		$('#user_spec select').change(function() {
		var selectedId = $(this).val();
			location.href = selectedId
		});
	}
	*/
	/*
	var setNavHeight = function ()
	{
		var winH = window.innerHeight;
		//var navHeight = winH - $('#header').height();
		var navHeight = winH - $('#nav').offset().top ;// - $('#footer').outerHeight();
		$('#nav').height( navHeight );
	}
	*/
	//表示するページのメニューをアクティブにナビを展開
	var setNavActiveCurrent = function()
	{
		var url = window.location.href;
		var myFileName = url.split('/').pop();

		if( myFileName.indexOf('#') > 0){
			myFileName = myFileName.replace(/\#.*$/, '');
		}
		//2025.02.19
		if( myFileName.indexOf('p2') > 0){
			myFileName = myFileName.replace(/(\?p2)[^&]*/, '$1');
		}
		//2025.03.10
		if( myFileName.indexOf('?') > 0){
			myFileName = myFileName.replace(/\?.*$/, '');
		}
		$('#nav a').each(function(){
			var href = $(this).attr('href');
			var result = href.indexOf( myFileName );
			if( result > 0 && myFileName != 'index.html'){
				$(this).parents('li').addClass('active').children('ul').show();
				return false
			}
		})
	}
	//
});

// GAログテスト用20210112
// goodボタン
$(function(){
	$("[class^='Questionnaire_Btn-good']").click(function(){
		$(this).addClass('-selected');
		$("[class^='Questionnaire_Btn-normal']").removeClass('-selected');
		$("[class^='Questionnaire_Btn-bad']").removeClass('-selected');
	});
});
// normalボタン
$(function(){
	$("[class^='Questionnaire_Btn-normal']").click(function(){
		$(this).addClass('-selected');
		$("[class^='Questionnaire_Btn-good']").removeClass('-selected');
		$("[class^='Questionnaire_Btn-bad']").removeClass('-selected');
	});
});
// badボタン
$(function(){
	$("[class^='Questionnaire_Btn-bad']").click(function(){
		$(this).addClass('-selected');
		$("[class^='Questionnaire_Btn-normal']").removeClass('-selected');
		$("[class^='Questionnaire_Btn-good']").removeClass('-selected');
	});
});
