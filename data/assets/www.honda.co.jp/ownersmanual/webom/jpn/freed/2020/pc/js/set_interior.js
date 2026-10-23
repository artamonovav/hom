
$(function ($) {

	$(window).load(function() { 


		$view = $('#graphic ul.changeView');


		$li_first = $('#interior ul.changeView li:first-child');
		$li_last = $('#interior ul.changeView li:last-child');

		$li_first.point({ pointList: dataListFront});
		$li_last.point({ pointList: dataListRear});

		$('#interior ul#horizontalScroll li').click(function(){
			$li_first.data('point').closePop() ;
			$li_last.data('point').closePop() ;
		})
		$('#interior ul#frontRearView li').click(function(){
			$li_first.data('point').closePop() ;
			$li_last.data('point').closePop() ;
		});

		//add 2018.08
		if( location.hash == "#seat" ){
			//$li_first
			$('#frontRearView li:first-child').removeClass('active');
			$('#frontRearView li:last-child').addClass('active');

			$('.changeView li:last-child').removeClass('active');
			$('.changeView li:last-child').addClass('active');

			$view.interior({selectIndex: 1 });
		}else{
			$view.interior({selectIndex: 0 });
		}
	});

});