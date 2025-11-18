names=$(./interface.py search "bitcoin hit december" -n 100 | ./interface.py get_names | grep -E "will-bitcoin-(re|di|hi).*/Yes" | head -n 25 | sort)
while :;
do
	display=""
	for name in $names;
	do
		id=$(./interface.py get_id $name);
		display=$(printf '%s\n' "$display" "$(echo $id | ./interface.py get_books -d 1 -p 1000 -n)")
	done;
	clear;
	echo "$display"
done

yes=$(./interface.py get_id will-bitcoin-dip-to-80000-by-december-31-2025-118-573-457/Yes)
echo $yes
echo $yes | ./interface.py get_names
read
while :;do y=$(echo $yes | ./interface.py get_names); z=$(echo $yes | ./interface.py get_books -d 4 -p 4); clear; echo $y; echo "$z"; sleep 2; done
