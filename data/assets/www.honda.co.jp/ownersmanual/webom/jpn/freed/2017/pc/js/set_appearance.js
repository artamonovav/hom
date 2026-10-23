	jQuery(function ($) {
		var timer = false;
		$(window).load(function(){
			$view = $('#graphic ul.changeView');

			$li_first = $('#appearance ul.changeView li:first-child');
			$li_last = $('#appearance ul.changeView li:last-child');

			$li_first.point({ pointList: dataListFront});
			$li_last.point({ pointList: dataListRear});

			$('#appearance ul#horizontalScroll li').click(function(){
				$li_first.data('point').closePop() ;
				$li_last.data('point').closePop() ;
			})
			$('#appearance ul#frontRearView li').click(function(){
				$li_first.data('point').closePop() ;
				$li_last.data('point').closePop() ;
				var index = $(this).index();
				if( index == 0 ){
					history.replaceState('', document.title, window.location.pathname);
				}else{
					var hashString = '#rear'
                    history.replaceState('', document.title, window.location.pathname + hashString);
				}
			})

			setImgSize( $('#graphic li').eq(0).find('img'));
			setImgSize( $('#graphic li').eq(1).find('img'));

			$(window).resize(function() {
				if (timer !== false) {
					clearTimeout(timer);
				}
				timer = setTimeout(function() {
					setImgSize( $('#graphic li').eq(0).find('img'));
					setImgSize( $('#graphic li').eq(1).find('img'));
				}, 100);
			});

			//add 2018.08
			if( location.hash == "#rear" ){
				//$li_first
				$('#frontRearView li:first-child').removeClass('active');
				$('#frontRearView li:last-child').addClass('active');

				$('.changeView li:last-child').removeClass('active');
				$('.changeView li:last-child').addClass('active');
			}
		});
		//

		var setImgSize = function( target ){
			target.parents().show();

			var size = getAppearancePosSize( target.width() ,target.height());
			if( size.top <= 0 ){
				//横長
				target.css( {'width':'auto','height':size.h, 'margin-left': size.left, 'margin-top':0 });
			}else{
				//縦長
				target.css( {'height':'auto','width':size.w, 'margin-top': size.top, 'margin-left':0 });
			}
		}
		var getAppearancePosSize = function( w, h )
		{
			var targetSize = new Object();
			targetSize.left = 0;	 //左右センターの場合の右側からの位置
			targetSize.top = 0;		 //上下ミドルの場合の上側からの位置

			var gW = $('#graphic').width();
			var gH = $('#graphic').height();

			var scaleX = w/gW;
			var scaleY = h/gH;

			if( scaleX > scaleY){
				//width 100%に
				targetSize.h =  Math.floor( h * ( gW / w ));
				targetSize.w =  gW;
				targetSize.top = Math.floor(( gH - targetSize.h )/2);
			}else{
				//height 100%に
				targetSize.h = gH;
				targetSize.w = Math.floor( w * ( gH / h ));
				targetSize.left = Math.floor(( gW - targetSize.w )/2);
			}
			return targetSize;
			//console.log(targetSize);
		}
		//
	});