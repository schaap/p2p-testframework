<?php
    $parserName = $argv[1];
    $logDir = $argv[2];
    $parsedLogDir = $argv[3];

    if( !file_exists( $logDir."/log.log" ) ) {
        echo "parser:aria2 (PHP) :: Parser ".$parserName." expected log file \"".$logDir."/log.log\", but it's not there.";
        exit( 1 );
    }

    if( file_exists( $parsedLogDir."/log.data" ) ) {
        echo "parser:aria2 (PHP) :: Data file \"".$parsedLogDir."/log.data\" should be created by parser ".$parserName.", but it already exists.";
        exit( 1 );
    }

    $output = "time percent upspeed dlspeed\n";
    $output .= "0 0 0 0\n";

    $firstTime=-1;
    $relTime=-1;
    $firstDay="";
    $lastRelTime="";

    $input_s = file_get_contents( $logDir."/log.log" );
    $input = explode( "\n", $input_s );

    foreach( $input as $LINE ) {
        if( $firstTime == -1 ) {
            if( !preg_match( "@^ \\*\\*\\* Download Progress Summary as of [^ ]*  *[^ ]*  *([0-9][0-9]*)  *([0-9][0-9]*):([0-9][0-9]*):([0-9][0-9]*) .*$@", $LINE, $m ) )
                continue;
            $firstDay = $m[1];
            $firstTime = $m[4] + 60 * $m[3] + 3600 * $m[2];
            $relTime = 1;
            continue;
        }

        if( preg_match( "@^ \\*\\*\\* Download Progress Summary as of [^ ]*  *[^ ]*  *([0-9][0-9]*)  *([0-9][0-9]*):([0-9][0-9]*):([0-9][0-9]*) .*$@", $LINE, $m ) ) {
            $relTime = $m[4] + 60 * $m[3] + 3600 * $m[2];
            if( $firstDay != $m[1] )
                $relTime += 24 * 3600;
            $relTime = $relTime - $firstTime;
            continue;
        }

        if( preg_match( "@NOTICE - Download complete@", $LINE ) ) {
            if( $relTime == -1 )
                $relTime = $lastRelTime + 1;
            $output .= "$relTime 100.0 0 0\n";
            $relTime = -1;
        }

        if( $relTime == -1 )
            continue;

        if( preg_match( "@^\\[\\#1 SIZE:0B/0B CN:[0-9]* SPD:0Bs.*@", $LINE ) ) {
            $output .= "$relTime 0 0 0\n";
            $lastRelTime = $relTime;
            $relTime = -1;
            continue;
        }

        if( preg_match( "@^\\[\\#1 SIZE:([0-9]*)B/([0-9]*)B\\([0-9]*%\\) CN:[0-9]* SPD:([0-9]*)Bs ETA:.*\\]$@", $LINE, $m ) ) {
            $percentDone = 100.0*($m[1]/$m[2]);
            $downspeed = $m[3] / 1024.0;
            
            $output .= "$relTime $percentDone 0 $downspeed\n";

            $lastRelTime = $relTime;
            $relTime = -1;
            continue;
        }
    }

    file_put_contents( $parsedLogDir."/log.data", $output );

    if( !file_exists( $parsedLogDir."/log.data" ) ) {
        echo "parser:aria2 (PHP) :: Could not output file ".$parsedLogDir."/log.data.";
        exit( -1 );
    }
    exit( 0 );
?>

