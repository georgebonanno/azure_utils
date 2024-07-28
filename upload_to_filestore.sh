#!/bin/bash

set -e

. $(dirname $0)/url.sh

if [ $# -ne 1 ]; then
	echo "usage: $0 path_to_file_to_upload"
fi

function upload_to_azure_fstore() {

f="$1"
[ -f $f ] || { echo "$f does not exist"; echo "exiting..."; exit 1;}
fname=$(basename $f)
size=$(du -b $f | cut -f1)

curl --insecure --verbose -X PUT -H "x-ms-version: 2021-06-08" -H "x-ms-date: $(date +Y-%m-%d)" -H "x-ms-type: file" -H "x-ms-content-length:$size" -H "Content-Length: 0" "$url/$fname?$params"

start=0
chunk_size=3000000

while [ 1 ]; do
	end=$(( $start + $chunk_size ))
	if [ $end -gt $size ]; then
		end=$size
	fi
	echo "$start"
	d=$(( $end - $start ))
	dd skip=$start count=$d if=$f of=/tmp/part  iflag=skip_bytes,count_bytes; #cat <(echo -n 'data: ') /tmp/part <(echo "")
	curl --insecure --verbose -T /tmp/part -H "x-ms-version:2021-06-08" -H "x-ms-range:bytes=$start-$(( $end-1 ))" -H "x-ms-date: $(date +%Y-%m-%d)" -H "x-ms-write:update" "$url/$fname?comp=range&$params"
	start=$(( $start+$chunk_size ))
	if [ $end -eq $size ]; then
		break;
	fi
	done
}

upload_to_azure_fstore $1