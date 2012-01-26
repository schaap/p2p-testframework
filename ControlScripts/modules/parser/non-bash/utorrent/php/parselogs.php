<?php
    $parserName = $argv[1];
    $logDir = $argv[2];
    $parsedLogDir = $argv[3];

    if( !file_exists( $logDir."/log.log" ) ) {
        echo "parser:utorrent (PHP) :: Parser ".$parserName." expected log file \"".$logDir."/log.log\", but it's not there.";
        exit( 1 );
    }

    if( file_exists( $parsedLogDir."/log.data" ) ) {
        echo "parser:utorrent (PHP) :: Data file \"".$parsedLogDir."/log.data\" should be created by parser ".$parserName.", but it already exists.";
        exit( 1 );
    }

    $output = "time percent upspeed dlspeed\n";
    $output .= "0 0 0 0\n";

    $firstTime=-1;
    $relTime=-1;
    $up_bytes=0;
    $down_bytes=0;
    $percentDone="";
    $prevDown=0;
    $prevUp=0;

    $input_s = file_get_contents( $logDir."/log.log" );
    $input = explode( "\n", $input_s );

    foreach( $input as $LINE ) {
        if( $firstTime == -1 ) {
            if( !preg_match( "@^[[:digit:]]*\\.[[:digit:]]*$@", $LINE ) )
                continue;
            $firstTime = $LINE;
        }

        if( preg_match( "@^[[:digit:]]*\\.[[:digit:]]*$@", $LINE ) ) {
            $relTime = $LINE - $firstTime;
            continue;
        }

        if( $relTime == -1 )
            continue;

        if( preg_match( "@^\\[\".*\",.*,.*,.*,.*,.*,.*,.*,.*@", $LINE ) ) {
            $m = array();
            preg_match( "@^[^,]*,[^,]*,[^,]*,[^,]*,([^,]*),([^,]*),([^,]*),.*$@", $LINE, $m );
            $percentDone = $m[1] / 10.0;
            $down = $m[2];
            $up = $m[3];
            if( $up < $prevUp )
                $up = $prevUp;
            if( $down < $prevDown )
                $down = $prevDown;
            $downspeed = ( $down - $prevDown ) / 1024.0;
            $upspeed = ( $up - $prevUp ) / 1024.0;
            $prevDown = $down;
            $prevUp = $up;

            $output .= "$relTime $percentDone $upspeed $downspeed\n";

            $relTime = -1;
        }
    }

    file_put_contents( $parsedLogDir."/log.data", $output );

    if( !file_exists( $parsedLogDir."/log.data" ) ) {
        echo "parser:utorrent (PHP) :: Could not output file ".$parsedLogDir."/log.data.";
        exit( -1 );
    }
    exit( 0 );
?>

