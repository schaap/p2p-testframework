<?php
    $parserName = $argv[1];
    $logDir = $argv[2];
    $parsedLogDir = $argv[3];

    if( !file_exists( $logDir."/log.log" ) ) {
        echo "parser:swift (PHP) :: Parser ".$parserName." expected log file \"".$logDir."/log.log\", but it's not there.";
        exit( 1 );
    }

    if( file_exists( $parsedLogDir."/log.data" ) ) {
        echo "parser:swift (PHP) :: Data file \"".$parsedLogDir."/log.data\" should be created by parser ".$parserName.", but it already exists.";
        exit( 1 );
    }

    $output = "time percent upspeed dlspeed\n";
    $output .= "0 0 0 0\n";

    $relTime=0;
    $up_bytes=0;
    $down_bytes=0;

    $input_s = file_get_contents( $logDir."/log.log" );
    $input = explode( "\n", $input_s );

    foreach( $input as $LINE ) {
        if( preg_match( "@^SLEEP@", $LINE ) ) {
            $relTime++;
        }

        if( preg_match( "@^[Dd][Oo][Nn][Ee]@", $LINE ) ) {
            $split = preg_split( "@[ ,()]@", $LINE );
            // Note that the indices are different from bash: the split works slightly different (i.e. some empty entries are included)
            $dlspeed = ($split[16] - $down_bytes)/1024.0;
            $down_bytes = $split[16];
            $upspeed = ($split[10] - $up_bytes)/1024.0;
            $up_bytes = $split[10];

            $percent = 0;
            if( $split[3] > 0 ) {
                $percent = 100 * ( $split[1] / $split[3] );
            }

            $output .= "$relTime $percent $upspeed $dlspeed\n";
            $relTime++;
        }
    }

    file_put_contents( $parsedLogDir."/log.data", $output );

    if( !file_exists( $parsedLogDir."/log.data" ) ) {
        echo "parser:swift (PHP) :: Could not output file ".$parsedLogDir."/log.data.";
        exit( -1 );
    }
    exit( 0 );
?>

