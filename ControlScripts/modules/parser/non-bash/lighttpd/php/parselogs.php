<?php
    $parserName = $argv[1];
    $logDir = $argv[2];
    $parsedLogDir = $argv[3];

    if( !file_exists( $logDir."/log.log" ) ) {
        echo "parser:lighttpd (PHP) :: Parser ".$parserName." expected log file \"".$logDir."/log.log\", but it's not there.";
        exit( 1 );
    }

    if( file_exists( $parsedLogDir."/log.data" ) ) {
        echo "parser:lighttpd (PHP) :: Data file \"".$parsedLogDir."/log.data\" should be created by parser ".$parserName.", but it already exists.";
        exit( 1 );
    }

    $output = "time percent upspeed dlspeed\n";
    $output .= "0 100.0 0 0\n";

    $firstTime=-1;
    $relTime=-1;
    $lastRelTime="";
    $up_bytes=0;
    $down_bytes=0;
    $lastUploaded=0;
    $newUploaded="";

    $input_s = file_get_contents( $logDir."/log.log" );
    $input = explode( "\n", $input_s );

    foreach( $input as $LINE ) {
        if( $firstTime == -1 ) {
            if( preg_match( "@^[0-9]*\\.[0-9]*$@", $LINE ) )
                $firstTime = $LINE;
            continue;
        }

        if( preg_match( "@^[0-9]*\\.[0-9]*$@", $LINE ) ) {
            $relTime = $LINE - $firstTime;
            continue;
        }

        if( $relTime == -1 )
            continue;

        if( preg_match( "@^Total kBytes: ([0-9]*)$@", $LINE, $m ) ) {
            $upspeed = $m[1] - $lastUploaded;
            $lastUploaded = $m[1];
            $output .= "$relTime 100.0 $upspeed 0\n";
            $relTime = -1;
        }
    }

    file_put_contents( $parsedLogDir."/log.data", $output );

    if( !file_exists( $parsedLogDir."/log.data" ) ) {
        echo "parser:lighttpd (PHP) :: Could not output file ".$parsedLogDir."/log.data.";
        exit( -1 );
    }
    exit( 0 );
?>

