
/* last update 2015.04.22 */


jQuery(function ($) {
	var timer = false;
	$(window).load(function(){

		Library.setSearchNav();
		setH1Prev();
		setChangeNav();
		setIntrospectionHeight();
		
		Library.setMore();
		Library.setNav();
		Library.setNavHeight();
		if( $('body#appearance').length >0 ||  $('body#interior').length > 0 ){
			Library.preload(['../images/common/point_on.png', '../images/common/point_off.png','../images/common/blue_opacity.png']);
		}
		$(window).resize(function() {
			if (timer !== false) {
				clearTimeout(timer);
			}
			timer = setTimeout(function() {
				Library.setNavHeight();
			}, 200);
		});

		$(window).scroll(function () {
			
		});
		
	//load
	});

	function setSlide()
	{
		$('#screen').css({'marginLeft':'20px'}).animate({
			'marginLeft': '0px'
		},200);
	}



	function setH1Prev(){
		var speed = 300;
		if( $('h1.has_prev a').length <= 0 ){
			$('h1.has_prev').click(function(){
				goPrev();
			})
		}
	}
	
	function goPrev()
	{
		history.back(-1);
	}
	function goForward()
	{
		history.forward();
	}
	
	function setIntrospectionHeight()
	{
		
	}
	


	//////////////////////////////////

	function setChangeNav(){
		var carG = $('#frontRearView li');
		$('#frontRearView li').click(
			function(){
				changeGraphicChange( $(this).index(), $('#appearance #graphic ul.changeView'), $('#appearance #frontRearView'));
			}
		);
		//
		changeGraphicChange( 0, $('#appearance #graphic ul.changeView'), $('#appearance #frontRearView'));
	}

	function changeGraphicChange( index , car, nav )
	{

		var myIndex = index;
		var carG_li = car.children('li');
		carG_li.hide();
		$(carG_li[myIndex]).addClass('active').fadeIn();
		
		var nav_li = nav.children('li');
		nav_li.removeClass('active');
		$(nav_li[myIndex]).addClass('active');
	}

	function hideNav(){
		$('#nav').transition({x: -$('#nav').width() }, 300,function(){ $(this).hide(); });
		$('#tabNav').removeClass( 'active' );
	}
	function showNav(){
		$('#nav').show().transition({x: 0}, 300);
		$('#tabNav').addClass( 'active' );
	}
	//
});


