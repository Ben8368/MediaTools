package utils

import (
	"crypto/aes"
	"errors"
	"fmt"
)

func PKCS7UnPadding(encrypt []byte) ([]byte, error) {
	if len(encrypt) == 0 {
		return nil, errors.New("pkcs7: empty input")
	}
	length := len(encrypt)
	unPadding := int(encrypt[length-1])
	if unPadding == 0 || unPadding > length || unPadding > 16 {
		return nil, errors.New("pkcs7: invalid padding value")
	}
	// 验证 padding 字节一致性
	for i := length - unPadding; i < length; i++ {
		if encrypt[i] != byte(unPadding) {
			return nil, errors.New("pkcs7: inconsistent padding")
		}
	}
	return encrypt[:length-unPadding], nil
}

func DecryptAES128ECB(data, key []byte) ([]byte, error) {
	cipher, err := aes.NewCipher(key)
	if err != nil {
		return nil, fmt.Errorf("aes new cipher: %w", err)
	}
	decrypted := make([]byte, len(data))
	size := 16
	for bs, be := 0, size; bs < len(data); bs, be = bs+size, be+size {
		cipher.Decrypt(decrypted[bs:be], data[bs:be])
	}
	return decrypted, nil
}
